"""Native evidence comparisons, synthetic PDFs only; no model or OCR calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fitz
import test_saved_review as support
from probe.common import atomic_json, files_manifest, read_json, sha
from probe import native_text_pilot as pilot
from probe.saved_pages import saved_pages


def block(identity='p:b0', text='A plain test.', box=None, kind='text'):
    return {'id':identity, 'kind':kind, 'bbox':box or [.05,.05,.95,.95],
            'native':{'content':text if kind=='equation' else [{'type':'text','content':text}]}}


def raw(text):
    return {'blocks':[{'lines':[{'dir':[1,0], 'spans':[{'font':'TestFont','size':10,'flags':0,
        'chars':[{'c':c,'bbox':[10+i,20,11+i,30],'origin':[10+i,28]} for i,c in enumerate(text)]}]}]}]}


class NativeComparisonTests(unittest.TestCase):
    def setUp(self):
        self.geo={'rect':[0,0,200,100],'rotation':0}
        self.page={'page_id':'p','page':{'selected_page':1,'original_physical_page':106,'owner':True},
                   'blocks':[block()]}

    def test_disjoint_original_selection_and_context_overlap(self):
        pages=[{'source_id':'s','page':{'original_physical_page':n,'selected_page':i+1,'owner':True}}
               for i,n in enumerate([106,170,206])]
        pages.append({'source_id':'s','page':{'original_physical_page':106,'selected_page':1,'owner':False}})
        sample={'version':1,'source_id':'s','development_original_pages':[170,106],'holdout_original_pages':[206]}
        selected=pilot.sample_pages(pages,sample)
        self.assertEqual([p['page']['selected_page'] for p in selected['development']],[2,1])
        for wrong in ([170,170],[170,206],[999]):
            with self.assertRaises(ValueError):pilot.sample_pages(pages,{**sample,'development_original_pages':wrong})
        with self.assertRaisesRegex(ValueError,'Duplicate owned'):
            pilot.sample_pages(pages+[pages[0]],sample)

    def test_crop_offset_is_not_added_to_native_coordinates_and_rotation_refuses(self):
        with fitz.open() as doc:
            p=doc.new_page(width=400,height=500)
            p.insert_text((120,150),'A plain test.')
            p.set_cropbox(fitz.Rect(100,100,350,450))
            geo=pilot.checked_geometry(p,p,{'width_points':250,'height_points':350})
            self.assertEqual(pilot.point_box([0,0,1,1],geo),[0,0,250,350])
            extracted=p.get_text('rawdict')
            char=pilot.characters(extracted)[0]
            self.assertAlmostEqual(char['origin'][0],20)
            b=block(box=[.07,.09,.5,.18])
            records,_=pilot.compare_page({**self.page,'blocks':[b]},extracted,geo)
            self.assertEqual(records[0]['native_text'],'A plain test.')
            p.set_rotation(90)
            with self.assertRaisesRegex(ValueError,'Rotated'):pilot.checked_geometry(p,p,{'width_points':350,'height_points':250})

    def test_geometry_mismatch_refused(self):
        with fitz.open() as a, fitz.open() as b:
            p=a.new_page(width=200,height=100); q=b.new_page(width=201,height=100)
            with self.assertRaisesRegex(ValueError,'geometry differs'):
                pilot.checked_geometry(p,q,{'width_points':200,'height_points':100})

    def test_missing_and_duplicate_regions_not_forced_to_match(self):
        self.page['blocks']=[block(),block('p:b1'),block('p:b2',box=[.8,.8,.9,.9])]
        records,unused=pilot.compare_page(self.page,raw('A plain test.'),self.geo)
        self.assertEqual([r['alignment'] for r in records],['ambiguous','ambiguous','unmatched'])
        self.assertTrue(unused['duplicate_claims'])
        self.assertIn('unmatched_region',records[2]['flags'])
        self.page['blocks']=[]
        records,unused=pilot.compare_page(self.page,raw('absent'),self.geo)
        self.assertEqual(len(unused['unassigned_characters']),6)

    def test_punctuation_signs_scripts_inequalities_ligatures_and_hyphens_preserved(self):
        for text in ['x − 1 ≤ y²;','x - 1 < y_2,','ﬁnite','co-\nvariance']:
            self.assertEqual(pilot.normalized(text),' '.join(text.split()))
        self.assertNotEqual(pilot.normalized('−1'),pilot.normalized('-1'))
        self.assertNotEqual(pilot.normalized('ﬁnite'),pilot.normalized('finite'))
        self.assertNotEqual(pilot.normalized('co-\nvariance'),pilot.normalized('covariance'))
        self.assertEqual(pilot.normalized('x\x0b y\x0c'), 'x\x0b y\x0c')
        records,_=pilot.compare_page(self.page,raw('A plain test,'),self.geo)
        self.assertEqual(records[0]['alignment'],'matched_anchors')
        self.assertIn('extraction_disagreement',records[0]['flags'])

    def test_native_math_never_becomes_accepted_even_when_surface_matches(self):
        self.page['blocks']=[block(text='x=1',kind='equation')]
        records,_=pilot.compare_page(self.page,raw('x=1'),self.geo)
        r=records[0]
        self.assertEqual(r['alignment'],'matched_exact')
        self.assertIn('native_math_incomplete',r['flags'])
        self.assertFalse(r['candidate']['eligible_for_automatic_application'])
        self.assertEqual(r['candidate']['status'],'UNACCEPTED')
        self.assertNotIn('suggested_latex',r)
        from probe.acceptance import validated_selection
        with self.assertRaisesRegex(ValueError,'Unsupported acceptance'):
            validated_selection(Path('/unused'),r['candidate'])

    def test_suspicious_glyph_and_exact_unflagged_control(self):
        records,_=pilot.compare_page(self.page,raw('A plain test.'),self.geo)
        self.assertEqual(records[0]['flags'],{})
        records,_=pilot.compare_page(self.page,raw('A plain \ufffd test. ﬁ'),self.geo)
        self.assertIn('missing_or_suspicious_glyph',records[0]['flags'])
        self.assertIn('ligature_present',records[0]['flags'])
        records,_=pilot.compare_page(self.page,raw('A plain \x0btest\x0c'),self.geo)
        self.assertIn('missing_or_suspicious_glyph',records[0]['flags'])


class NativePilotIntegrationTests(unittest.TestCase):
    def setUp(self):
        support.SavedReviewTests.setUp(self)
        reg=self.state['settings']['sources']['fixture-native'];reg['manifest']='preparation.json'
        atomic_json(self.root/'preparation.json',{'selected_pdf':{'sha256':reg['sha256']},
            'pages':[{'selected_page_1based':i+1,'original_physical_page_1based':i+21} for i in range(2)]})
        atomic_json(self.root/'sources.json',self.state['settings']['sources'])
        atomic_json(self.run/'state.json',self.state)
        self.sample=self.root/'sample.json'
        atomic_json(self.sample,{'version':1,'source_id':'fixture-native',
            'development_original_pages':[21],'holdout_original_pages':[22]})
        self.pilot=self.root/'pilot'

    def test_frozen_split_neutral_pack_and_original_evidence_preserved(self):
        before=files_manifest(self.run)
        with patch('socket.socket',side_effect=AssertionError('No network')),patch('subprocess.run',side_effect=AssertionError('No workers')):
            pilot.prepare(self.root,self.run,self.sample,self.pilot)
            self.assertFalse((self.pilot/'holdout').exists())
            dev=files_manifest(self.pilot/'development')
            pdf,pages=pilot.frozen_inputs(self.root,self.pilot)
            pilot.run_stage(self.pilot,'holdout',pdf,pages['holdout'])
            selection=self.root/'pack.json'
            atomic_json(selection,{'block_ids':['fixture-native-p0001:b1','fixture-native-p0002:b3']})
            dest=pilot.pack(self.root,self.pilot,selection)
        self.assertEqual(files_manifest(self.run),before)
        self.assertEqual(files_manifest(self.pilot/'development'),dev)
        text=(dest/'regions.json').read_text()
        for prohibited in ('GOLD_ONLY_SENTINEL','expected_answer','flags','alignment','split'):
            # Font flags in character metadata are raw evidence, not selection diagnoses.
            if prohibited!='flags':self.assertNotIn(prohibited,text)
        self.assertEqual(len(read_json(dest/'regions.json')),2)
        pilot.verify_seal(dest)
        atomic_json(selection,{'block_ids':['fixture-native-p0001:b1'],'expected':'ANSWER'})
        with self.assertRaisesRegex(ValueError,'not diagnoses'):
            pilot.pack(self.root,self.pilot,selection)
        atomic_json(selection,{'block_ids':['fixture-native-p0001:b1','fixture-native-p0002:b3']})
        with self.assertRaises(FileExistsError):pilot.pack(self.root,self.pilot,selection)
        with self.assertRaises(FileExistsError):pilot.run_stage(self.pilot,'holdout',pdf,pages['holdout'])

    def test_changed_rules_code_sample_or_source_refuses_holdout(self):
        pilot.prepare(self.root,self.run,self.sample,self.pilot)
        for filename in ('rules.json','sample.json','bindings.json','development/comparisons.json'):
            p=self.pilot/filename;before=p.read_bytes();p.write_bytes(before+b' ')
            with self.assertRaises(ValueError):pilot.frozen_inputs(self.root,self.pilot)
            p.write_bytes(before)
        with patch.dict(pilot.RULES,anchor_min_count=99):
            with self.assertRaisesRegex(ValueError,'rules differ'):pilot.frozen_inputs(self.root,self.pilot)
        p=self.root/'fixture-native.pdf';p.write_bytes(p.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):pilot.frozen_inputs(self.root,self.pilot)

    def test_bad_manifest_refused_before_output(self):
        p=self.root/'preparation.json';m=read_json(p);m['pages'][0]['original_physical_page_1based']=99
        atomic_json(p,m)
        with self.assertRaisesRegex(ValueError,'mapping differs'):
            pilot.prepare(self.root,self.run,self.sample,self.pilot)
        self.assertFalse(self.pilot.exists())
