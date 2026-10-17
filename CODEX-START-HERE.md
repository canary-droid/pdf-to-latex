# Using Codex on the Spark with your private GitHub repository

Prepared 17 October 2026. Run the commands yourself, one block at a time. Stop
at an unexpected error and retain its exact text. None of these Spark setup
commands has been executed by the authoring assistant.

Your checkout is the project folder on the Spark. Its ordinary files are the
working tree. A commit is a local saved revision; a push copies committed
revisions to GitHub. Codex edits the working tree. You inspect it, stage selected
changes, commit and push. Codex must never perform those Git writes for you.

The Codex client and its tools run on the head Spark; development prompts and
selected context are sent to OpenAI. It does not run its coding model on your
Spark GPUs. The PDF conversion program still uses local GLM 5.3 Flash and local
OCR. No OpenRouter is involved. A private GitHub repository does not change
where Codex inference happens.

Use ChatGPT sign-in with the account holding your Pro subscription. Codex access
is included, subject to your plan allowance; API-key billing is separate.
See the official [pricing](https://learn.chatgpt.com/docs/pricing) and
[authentication](https://learn.chatgpt.com/docs/auth) documentation.

## 1. Connect to the head Spark

In **Windows PowerShell**:

```powershell
ssh mdi@192.168.1.100
```

Use your usual working SSH alias instead if the address has changed. Then, in
the **Spark terminal**:

```bash
hostname
uname -m
git --version
python3 --version
command -v curl
command -v bwrap
```

The expected architecture is `aarch64`. The second Spark does not need Codex
installed for this workflow. These checks do not contact the GLM endpoint.

If `bwrap` is missing, install the distribution's small sandbox helper yourself:

```bash
sudo apt update
sudo apt install bubblewrap
```

If Git or curl is missing, install only the missing package with `sudo apt
install git` or `sudo apt install curl`. These steps do not install Python
packages or replace system Python. Use your ordinary account for Codex itself.
The official [sandbox guide](https://learn.chatgpt.com/docs/sandboxing) recommends
the distribution bubblewrap package on Linux. If a namespace/AppArmor error
persists, share it for targeted diagnosis; do not disable sandboxing globally.

## 2. Install Codex under your own account

The current official [CLI guide](https://learn.chatgpt.com/docs/codex/cli) uses a
standalone Linux installer. We download it first so a failed download does not
look like a successful piped installation. No npm, Python environment or GPU
runtime is required for this installation route.

On the **Spark**:

```bash
mkdir -p "$HOME/Downloads"
curl -fL https://chatgpt.com/codex/install.sh -o "$HOME/Downloads/codex-install.sh"
```

After that download succeeds:

```bash
sh "$HOME/Downloads/codex-install.sh"
export PATH="$HOME/.local/bin:$PATH"
codex --version
```

Follow the installer's prompts. Its documented default command location is
`~/.local/bin`; follow any shell setup it prints. The `export` above affects only
this terminal. If `codex` is missing in a new SSH session, repeat that export or
add that exact line once to your `~/.bashrc`. See
[installer variables](https://learn.chatgpt.com/docs/config-file/environment-variables).

If the download returns an HTTP error or the binary reports an architecture or
library problem, stop there and share the error. Do not install an x86 build,
compile a replacement, or alter your working TensorFold environment to fix it.

## 3. Sign in using the Windows browser

In ChatGPT on your **Windows browser**, use the account with Pro and enable
device-code login in Settings → Security if that option is required/shown.
Then on the **Spark**:

```bash
codex login --device-auth
```

Open the link printed by that command in your Windows browser, sign in with
ChatGPT, and enter its one-time code. The terminal should complete the login.
Then run:

```bash
codex login status
```

Confirm it reports ChatGPT authentication. You do not need an OpenAI API key.
Keep login codes and `~/.codex/auth.json` out of chat and out of Git.

If device login is unavailable, the documented alternative is an SSH callback
tunnel. In a new **Windows PowerShell** window:

```powershell
ssh -L 1455:localhost:1455 mdi@192.168.1.100
```

In that new **Spark SSH session**:

```bash
export PATH="$HOME/.local/bin:$PATH"
codex login
```

Open its printed login URL in the Windows browser and keep that SSH session
open until login completes. This uses the official
[headless login instructions](https://learn.chatgpt.com/docs/auth#login-on-headless-devices).

## 4. Put the project on the Spark

Download `PDF_to_LaTeX_Codex_Starter_v1.zip` from this conversation to Windows
Downloads. It contains the existing probe, its inputs, the accepted design PDF,
and the new `AGENTS.md`/Git instructions. Keep this archive as an input backup.

In a separate **Windows PowerShell** terminal, outside the SSH session:

```powershell
scp "$env:USERPROFILE\Downloads\PDF_to_LaTeX_Codex_Starter_v1.zip" mdi@192.168.1.100:~/
```

On the **Spark**, extract into a new folder. This deliberately refuses to
overlay an existing checkout:

```bash
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile
base = Path.home() / 'local-llm'
target = base / 'pdf-to-latex'
if target.exists():
    raise SystemExit('Destination exists; keep it intact and choose a new folder.')
base.mkdir(parents=True, exist_ok=True)
with ZipFile(Path.home() / 'PDF_to_LaTeX_Codex_Starter_v1.zip') as archive:
    archive.extractall(base)
print(target)
PY
```

After successful extraction:

```bash
cd "$HOME/local-llm/pdf-to-latex"
ls
cat AGENTS.md
```

If you have already run the original probe package, retain that old directory
and its results. Do not discard runs or overwrite them with this starter.

## 5. Create the private repository and GitHub authentication

In your **Windows browser**, open [GitHub's new repository page](https://github.com/new).
Choose the name `pdf-to-latex` and **Private**. Leave README, license and gitignore
initialisation unchecked: the starter already has those project files. Create
the empty repository and keep its page open. See GitHub's
[existing-code instructions](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github).

Codex does not need a GitHub connector or repository OAuth authorisation for
this local workflow. GitHub authentication below is for your own Git commands.

If this Spark already authenticates successfully with GitHub SSH, reuse that
configuration and skip the new-key steps and `core.sshCommand` setting below.
Otherwise, on the **Spark**:

```bash
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
ssh-keygen -t ed25519 -C "Spark PDF-to-LaTeX" -f "$HOME/.ssh/id_ed25519_github_pdf2tex"
```

Choose a passphrase when prompted. If that exact key file already exists, answer
**no** to overwriting it and reuse it only if it is yours. This separate filename
avoids replacing the SSH key used between your Sparks.

Display the **public** part:

```bash
cat "$HOME/.ssh/id_ed25519_github_pdf2tex.pub"
```

In GitHub's browser settings, open **SSH and GPG keys → New SSH key**, choose an
authentication key, and paste that complete public-key line. The private file
without `.pub` stays on the Spark. Follow GitHub's
[key creation](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent?platform=linux)
and [key registration](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account?platform=linux) instructions.

Test that specific key on the **Spark**:

```bash
ssh -T -i "$HOME/.ssh/id_ed25519_github_pdf2tex" -o IdentitiesOnly=yes git@github.com
```

On a first connection, compare the displayed host-key fingerprint with
[GitHub's official fingerprints](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints)
before accepting it. Success is GitHub greeting your username and saying it
does not provide shell access; exit code 1 is normal for this authentication
test. See [testing SSH](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/testing-your-ssh-connection).

You can enter the key passphrase for each Git operation. Optionally load it once
into an SSH agent in your interactive terminal:

```bash
eval "$(ssh-agent -s)"
ssh-add "$HOME/.ssh/id_ed25519_github_pdf2tex"
```

## 6. Make the initial checkpoint yourself

The following are **your commands**, run at the ordinary Spark shell, outside
Codex. Replace the email and `YOUR_GITHUB_USERNAME` with your values. You can use
the GitHub-provided no-reply email shown in your GitHub email settings.

```bash
cd "$HOME/local-llm/pdf-to-latex"
git init -b main
git config user.name "Marco Iovine"
git config user.email "YOUR_GITHUB_EMAIL"
```

Only if you created the dedicated key above:

```bash
git config core.sshCommand "ssh -i '$HOME/.ssh/id_ed25519_github_pdf2tex' -o IdentitiesOnly=yes"
```

Then:

```bash
git remote add origin git@github.com:YOUR_GITHUB_USERNAME/pdf-to-latex.git
git status --short
git add --dry-run .
```

Review the proposed file list. It should include code, fixtures, instructions,
source-identification records and the design PDF. It should exclude `inputs/`,
model weights, virtual environments, local settings, credentials and raw runs.
No blanket PDF exclusion is used: project documents belong in the repository.

Once satisfied, stage and inspect the initial contents:

```bash
git add .
git diff --cached --stat
git diff --cached --check
git diff --cached
```

Press `q` to leave Git's pager. The initial diff includes new text files;
inspect binary PDFs using a PDF viewer. Then create and upload the checkpoint:

```bash
git commit -m "Import local PDF-to-LaTeX probe and Codex project instructions"
git push -u origin main
git status --short
```

The final status should be empty. Refresh GitHub to confirm the files and the
Private label. No Codex session has yet been asked to change anything.

## 7. Start Codex with the agreed boundary

From the **Spark project directory**:

```bash
codex --sandbox workspace-write --ask-for-approval never \
  -c sandbox_workspace_write.network_access=false
```

This permits ordinary project edits while the sandbox protects `.git` and
blocks network access by shell commands. `never` means Codex cannot obtain an
exception to that sandbox; it does not mean unrestricted access. The Codex
client can still communicate with OpenAI. `AGENTS.md` separately tells the
agent never to run commit/push, stage files, or modify other Git state.

Use `/status` to inspect the effective settings. Do not switch this session to
Full Access. These controls are documented in
[agent approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security)
and the [CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli).
The settings must work on your installed build; a sandbox error is a setup
problem to diagnose, not permission to continue unsandboxed.

Paste this first prompt:

```text
Read AGENTS.md, docs/CODEX-HANDOVER.md, docs/PROJECT-STATE.md, README.md and
START-HERE.md. Inspect the existing code and current git status.
Do not change files yet. Explain the implemented probe, distinguish offline
validation from untested Spark steps, and identify any immediate setup issue.
Confirm that you will edit only working-tree files and that I alone stage,
commit and push. Do not install dependencies, call GLM or start OCR yet.
```

Codex reads repository instructions automatically; see the official
[AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
It does not need this chat to recover the project. Leave the default model at
first; `/model` lets you see the models your account currently offers.

## 8. Continue this project and review each change

The pending project step is the preflight, not a new design. When GLM is serving
and free, run this yourself in a second Spark terminal in the same folder:

```bash
python3 probe.py preflight --peer spark-92a4
```

Tell Codex the exact run directory printed by the command and ask it to inspect
the results. A local network request, dependency download or OCR run may be
blocked inside the strict development sandbox, so run those explicit commands
yourself in the ordinary shell. Some offline tests also need loopback sockets;
if blocked, run them in your shell and give Codex the output. This does not
require giving Codex broader Git or machine access.

A useful subsequent prompt is:

```text
Inspect the preflight run at THE_ACTUAL_RUN_DIRECTORY. Explain what passed,
what failed and the smallest next step. If a code fix is needed, implement only
that fix in the working tree, run relevant allowed checks, and update
docs/PROJECT-STATE.md. Preserve raw evidence. Do not stage, commit or push.
Report any command I must run myself and suggest a commit message if useful.
```

Replace the run-directory placeholder. Do not mark OCR or fidelity as passed
merely because the endpoint accepts requests.

When Codex finishes, in your own terminal:

```bash
git status --short
git diff --stat
git diff --check
git diff
git ls-files --others --exclude-standard
```

`git diff` shows changes to tracked files. Newly created files appear in status
and the final command; open and review them too. For accepted changes, you can
stage selected existing-file hunks with `git add -p`, and add each accepted new
file with `git add path/to/file`. Then inspect and commit the exact staged diff:

```bash
git diff --cached --check
git diff --cached
git commit -m "YOUR_REVIEWED_COMMIT_MESSAGE"
git push
```

These commands remain yours. You can ask Codex for another edit or a review of
the unstaged diff before committing. If you decline a change, identify the file
or hunk; avoid indiscriminate reset/clean commands that could erase your work.

To continue later, return to the same directory and start Codex again. It will
read the repository instructions. To resume the latest local conversation:

```bash
codex --sandbox workspace-write --ask-for-approval never \
  -c sandbox_workspace_write.network_access=false resume --last
```

Repository documents and reviewed commits are the durable project record.
The chat is useful context, but it is not the only record of decisions or tests.

## What is and is not validated

This starter keeps the previously tested application bytes unchanged. The
original 59-test result remains in `docs/offline-tests.txt`. New material is
the Git/Codex workflow, instructions, source-provenance copies and design PDF.
Archive integrity and preserved file hashes were checked here. Codex install,
login, SSH authentication, GitHub publication and sandbox behaviour have **not**
been tested on your Spark. They become validated only when you run these steps.
