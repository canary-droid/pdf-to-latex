"""Durable SSE evidence for the opt-in simple chapter route, not another client."""
import json
import os
import time
from pathlib import Path

from .common import atomic_json


class DurableText:
    """Redact even when a credential straddles chunks; flush evidence on each feed."""
    def __init__(self, path, key=None):
        self.file = Path(path).open('wb'); self.key = key.encode() if key else None
        self.pending = b''

    def write(self, value):
        self.pending += value.encode('utf-8') if isinstance(value, str) else value
        if self.key: self.pending = self.pending.replace(self.key, b'[REDACTED_API_KEY]')
        keep = len(self.key) - 1 if self.key else 0
        count = max(0, len(self.pending) - keep)
        self.file.write(self.pending[:count]); self.pending = self.pending[count:]

    def flush(self):
        self.file.flush(); os.fsync(self.file.fileno())

    def close(self):
        self.file.write(self.pending); self.pending = b''; self.flush(); self.file.close()


class ChapterStream:
    """Preserve wire bytes and complete deltas; never accept an interrupted stream."""
    def __init__(self, folder, model, strict_json, key=None):
        self.folder = Path(folder); self.model = model; self.parse = strict_json
        self.raw = DurableText(self.folder / 'response.raw', key)
        self.reasoning = DurableText(self.folder / 'reasoning.txt', key)
        self.answer = DurableText(self.folder / 'answer.txt', key)
        self.events = DurableText(self.folder / 'stream-events.jsonl', key)
        self.pending = b''; self.data = []; self.done = False; self.finish = None
        self.actual_model = None; self.usage = {}; self.stats = {}; self.chunks = 0
        self.reasoning_parts = []; self.answer_parts = []; self.started = time.monotonic()
        self.key = key

    def feed(self, part):
        self.raw.write(part); self.raw.flush()  # save before parsing, including invalid events
        self.pending += part
        try:
            while b'\n' in self.pending:
                line, self.pending = self.pending.split(b'\n', 1); line = line.rstrip(b'\r')
                if not line:
                    if self.data: self.event(b'\n'.join(self.data)); self.data = []
                elif line.startswith(b'data:'):
                    self.data.append(line[5:].lstrip(b' '))
        finally:
            for sink in (self.reasoning, self.answer, self.events): sink.flush()

    def event(self, raw):
        if self.done: raise ValueError('Data after stream completion marker')
        if raw == b'[DONE]': self.done = True; return
        value = self.parse(raw.decode('utf-8'))
        if not isinstance(value, dict): raise ValueError('Stream event must be an object')
        self.chunks += 1
        self.events.write(json.dumps({'event': self.chunks, 'elapsed_seconds': time.monotonic() - self.started,
                                     'value': value}, ensure_ascii=False) + '\n')
        if value.get('error'): raise ValueError('Server stream error: ' + str(value['error']))
        model = value.get('model')
        if model is not None:
            self.actual_model = model
            if model != self.model: raise ValueError('Stream model identity mismatch: ' + str(model))
        choices = value.get('choices')
        if not isinstance(choices, list) or len(choices) > 1: raise ValueError('Expected one streamed choice')
        if isinstance(value.get('usage'), dict): self.usage = value['usage']
        if isinstance(value.get('tensorfold'), dict): self.stats = value['tensorfold']
        if not choices: return  # usage-only event
        choice = choices[0]
        if choice.get('index', 0) != 0: raise ValueError('Unexpected streamed choice index')
        delta = choice.get('delta', {})
        if not isinstance(delta, dict): raise ValueError('Invalid streamed delta')
        if delta.get('tool_calls') or delta.get('function_call'): raise ValueError('Tool output is not a chapter answer')
        for field, parts, sink in (('reasoning_content', self.reasoning_parts, self.reasoning),
                                   ('content', self.answer_parts, self.answer)):
            text = delta.get(field)
            if text is not None:
                if not isinstance(text, str): raise ValueError('Non-text streamed ' + field)
                if self.finish is not None and text: raise ValueError('Text after finish_reason')
                parts.append(text); sink.write(text)
        finish = choice.get('finish_reason')
        if finish is not None:
            if self.finish is not None: raise ValueError('Duplicate stream finish_reason')
            self.finish = finish

    def response(self):
        if not self.done or self.pending.strip() or self.data or not self.finish:
            raise ValueError('Interrupted/incomplete stream; partial text retained, never completion credit')
        if self.actual_model != self.model: raise ValueError('Stream did not identify the exact selected model')
        return self.assembled()

    def assembled(self):
        return {'model': self.actual_model, 'choices': [{'index': 0, 'finish_reason': self.finish,
                 'message': {'role': 'assistant', 'content': ''.join(self.answer_parts),
                             'reasoning_content': ''.join(self.reasoning_parts)}}],
                'usage': self.usage, 'tensorfold': self.stats,
                'stream_evidence': {'done_seen': self.done, 'events': self.chunks,
                                    'note': 'Locally assembled deltas; original wire response is response.raw'}}

    def close(self):
        for sink in (self.raw, self.reasoning, self.answer, self.events): sink.close()
        value = json.dumps(self.assembled(), ensure_ascii=False)
        if self.key: value = value.replace(self.key, '[REDACTED_API_KEY]')
        atomic_json(self.folder / 'response.assembled.json', json.loads(value))
