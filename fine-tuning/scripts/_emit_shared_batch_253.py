"""One-off emitter for shared-base batch-253 — technical domain (Git internals and advanced Git: objects, packfiles, refs, reflog, GC, rebase, worktrees, hooks, LFS, monorepo tools, forges).

Writes 50 rows to data/v2/shared/batch_253.tmp.jsonl with ids shared-12601..12650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_253.tmp.jsonl"
ID_OFFSET = 12600

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The Git object store keeps blob, tree, commit, and tag objects under .git/objects; a blob holds file content, a tree maps names to blobs, and a commit points at one tree plus its parents.", "reference", "technical", False,
     [("Git", "tool"), ("blob", "concept"), ("tree", "concept"), ("commit", "concept"), ("tag", "concept"), (".git/objects", "file")],
     [("Git", ".git/objects", "USES"), ("commit", "tree", "HAS_PART")],
     "what four object kinds live under the Git object directory and how do they relate",
     "git object store blob tree commit tag .git/objects"),
    # --- 2 ---
    ("We switched the mirror from loose objects to packfiles because a million loose files were exhausting inodes on ext4; `git repack -ad` now rolls the repo into a single .pack plus its .idx.", "decision", "technical", False,
     [("packfile", "concept"), ("loose objects", "concept"), ("git repack", "command"), ("ext4", "file"), (".pack", "file"), (".idx", "file")],
     [("packfile", "loose objects", "REPLACES"), ("git repack", "packfile", "PRODUCES")],
     "why did the mirror move to packfiles and which command rolls the repo into one",
     "git pack loose object inode ext4 repack idx mirror"),
    # --- 3 ---
    ("Delta compression in a Git packfile stores an object as an offset plus a diff against a base object; the window of candidate bases is set by `pack.window` and the search depth by `pack.depth`.", "reference", "technical", False,
     [("Delta compression", "algorithm"), ("packfile", "concept"), ("pack.window", "config"), ("pack.depth", "config")],
     [("packfile", "Delta compression", "USES")],
     "how does a packfile shrink object size and which two config knobs govern base selection",
     "git delta compression pack window depth base object diff"),
    # --- 4 ---
    ("refs/heads, refs/tags, and refs/remotes form the three main namespaces under .git/refs; `git pack-refs` collapses them into packed-refs to cut directory churn on repos with thousands of branches.", "architecture", "technical", False,
     [("refs/heads", "concept"), ("refs/tags", "concept"), ("refs/remotes", "concept"), ("packed-refs", "file"), ("git pack-refs", "command")],
     [("git pack-refs", "packed-refs", "PRODUCES")],
     "which three ref namespaces does Git expose and how does pack-refs help repos with many branches",
     "refs heads tags remotes packed-refs pack-refs namespace"),
    # --- 5 ---
    ("The reflog at .git/logs/HEAD saved us after a bad rebase: `git reflog` showed the pre-rebase tip and `git reset --hard HEAD@{4}` restored the branch without touching anyone else's clone.", "problem", "technical", False,
     [("reflog", "concept"), (".git/logs/HEAD", "file"), ("git reflog", "command"), ("git reset", "command"), ("rebase", "concept")],
     [("git reflog", "rebase", "FIXES"), ("git reset", "reflog", "USES")],
     "how did the reflog rescue a branch after a bad rebase and which reset flag completed the recovery",
     "git reflog reset hard HEAD rebase rescue recover"),
    # --- 6 ---
    ("Git garbage collection only prunes objects unreachable from any ref or reflog entry; setting `gc.reflogExpireUnreachable` shorter is what finally let `git gc --prune=now` actually drop the leaked blobs.", "problem", "technical", False,
     [("garbage collection", "concept"), ("reflog", "concept"), ("gc.reflogExpireUnreachable", "config"), ("git gc", "command")],
     [("garbage collection", "reflog", "USES")],
     "why did git gc refuse to drop leaked blobs and which reflog expiry setting unblocked it",
     "git gc prune reachability reflog expire unreachable leak"),
    # --- 7 ---
    ("HEAD is normally a symbolic ref pointing at a branch under refs/heads; a detached HEAD happens when you check out a commit directly, and new commits land on no branch until you name one.", "reference", "technical", False,
     [("HEAD", "concept"), ("symbolic ref", "concept"), ("detached HEAD", "concept"), ("refs/heads", "concept")],
     [("HEAD", "refs/heads", "COMMUNICATES_WITH")],
     "what does HEAD normally point at and what does detached HEAD mean for new commits",
     "head symbolic ref detached branch checkout commit orphan"),
    # --- 8 ---
    ("Rebase rewrites the branch by replaying commits on a new base, while merge preserves history with a merge commit; we standardised on rebase for feature branches and merge for release integration.", "decision", "technical", False,
     [("rebase", "concept"), ("merge", "concept"), ("feature branch", "pattern"), ("release integration", "pattern")],
     [("rebase", "feature branch", "APPLIES_TO"), ("merge", "release integration", "APPLIES_TO")],
     "how did we split rebase and merge across branch roles in the standard workflow",
     "git rebase merge feature branch release integration workflow"),
    # --- 9 ---
    ("Standardised on cherry-pick with `git cherry-pick -x` for porting security fixes from main to maintenance branches; the -x flag records the source SHA in the body so the audit trail survives.", "decision", "technical", False,
     [("cherry-pick", "concept"), ("git cherry-pick", "command"), ("main", "concept"), ("maintenance branches", "concept")],
     [("cherry-pick", "main", "APPLIES_TO")],
     "which cherry-pick flag did the team pick for porting security fixes and what audit trail does it leave",
     "git cherry pick security fix maintenance branch source sha audit"),
    # --- 10 noise ---
    ("The kitchen corkboard collected nine postcards from the same coastline before anyone noticed the pattern.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Interactive rebase via `git rebase -i HEAD~8` lets you squash, fixup, reword, or drop commits before pushing; fixup is the quiet cousin of squash that discards the marked commit's message.", "fact", "technical", False,
     [("Interactive rebase", "concept"), ("git rebase -i", "command"), ("squash", "concept"), ("fixup", "concept"), ("reword", "concept")],
     [("Interactive rebase", "squash", "USES"), ("fixup", "squash", "RELATED_TO")],
     "which actions does interactive rebase offer and how does fixup differ from squash",
     "git rebase interactive squash fixup reword drop commit"),
    # --- 12 ---
    ("`git reset --soft` keeps the index and working tree while rewinding HEAD, `--mixed` resets the index too, and `--hard` discards local changes; the soft variant is the rewrite-my-last-commit move.", "reference", "technical", False,
     [("git reset", "command"), ("--soft", "config"), ("--mixed", "config"), ("--hard", "config"), ("index", "concept"), ("working tree", "concept")],
     [("git reset", "index", "CONFIGURES")],
     "what do the three git reset modes each preserve or discard and which rewrites the last commit",
     "git reset soft mixed hard index working tree rewind"),
    # --- 13 ---
    ("Reflog rescue after `git reset --hard`: the lost commits sit under HEAD@{n} entries for the configured expiry (90 days by default), so a fresh branch at the right reflog slot recovers the work.", "fact", "technical", False,
     [("reflog", "concept"), ("git reset --hard", "command"), ("HEAD@{n}", "concept"), ("90 days", "date")],
     [("reflog", "git reset --hard", "FIXES")],
     "how long does the reflog hold commits lost to a hard reset and how do you bring them back",
     "reflog rescue reset hard head at n 90 day expiry branch"),
    # --- 14 ---
    ("We replaced the Git submodule layout with a git subtree because contributors kept forgetting `git submodule update --init --recursive`; subtree bakes the dependency into the super-repo history instead.", "decision", "technical", False,
     [("git submodule", "concept"), ("git subtree", "concept"), ("super-repo", "concept")],
     [("git subtree", "git submodule", "REPLACES")],
     "which Git embedding strategy replaced submodules and what contributor friction drove the swap",
     "git submodule subtree super repo update init recursive"),
    # --- 15 ---
    ("`git worktree add ../hotfix release-2026.03` let the on-call engineer patch production without stashing the feature work in the main checkout; each worktree has its own index and HEAD.", "milestone", "technical", False,
     [("git worktree", "command"), ("hotfix", "concept"), ("release-2026.03", "date"), ("index", "concept"), ("HEAD", "concept")],
     [("git worktree", "index", "PRODUCES")],
     "which Git mechanism gave the pager-duty responder a second checkout for a release-line patch without disturbing feature work",
     "git worktree add hotfix release index head parallel checkout"),
    # --- 16 ---
    ("Sparse-checkout with cone mode trims the working tree to the directories you actually touch; `git sparse-checkout set services/api libs/core` cut the checkout from 42 GB to 3 GB for the monorepo hires.", "milestone", "technical", False,
     [("Sparse-checkout", "concept"), ("cone mode", "concept"), ("git sparse-checkout", "command"), ("monorepo", "pattern")],
     [("Sparse-checkout", "cone mode", "USES")],
     "how did sparse-checkout shrink the working tree and which cone mode command drove the cut",
     "git sparse checkout cone mode monorepo trim working tree size"),
    # --- 17 ---
    ("Partial clone with `git clone --filter=blob:none` (the blobless variant) fetches commits and trees but defers blobs until checkout touches them; treeless (`--filter=tree:0`) goes further and defers trees too.", "reference", "technical", False,
     [("Partial clone", "concept"), ("blobless", "concept"), ("treeless", "concept"), ("git clone", "command"), ("--filter=blob:none", "config"), ("--filter=tree:0", "config")],
     [("Partial clone", "git clone", "USES")],
     "how do blobless and treeless partial clones differ in what they defer fetching",
     "git partial clone filter blob none tree zero defer fetch"),
    # --- 18 ---
    ("`git bundle create snapshot.bundle --all` produced an offline transfer artefact for the air-gapped build farm; the remote side runs `git clone snapshot.bundle` and fetches incrementally from it afterwards.", "milestone", "technical", False,
     [("git bundle", "command"), ("snapshot.bundle", "file"), ("air-gapped", "concept"), ("build farm", "infrastructure")],
     [("git bundle", "air-gapped", "APPLIES_TO")],
     "how does git bundle move a repository into an air-gapped environment for the build farm",
     "git bundle create all air gapped build farm offline transfer"),
    # --- 19 ---
    ("Signed commits moved from GPG to SSH signing with `gpg.format = ssh`; allowed-signers files replaced the GnuPG keyring and CI verifies every tag with `git verify-tag` before release.", "decision", "technical", False,
     [("Signed commits", "concept"), ("GPG", "technology"), ("SSH signing", "technology"), ("gpg.format", "config"), ("allowed-signers", "file"), ("git verify-tag", "command")],
     [("SSH signing", "GPG", "REPLACES"), ("git verify-tag", "Signed commits", "APPLIES_TO")],
     "why did we swap GPG signing for SSH and how does CI check tags before a release",
     "git signed commit gpg ssh format allowed signers verify tag"),
    # --- 20 ---
    ("Sigstore's gitsign lets developers sign commits with their OIDC identity and a short-lived certificate from Fulcio; no local key material and no keyring rotation to manage across the team.", "architecture", "technical", False,
     [("Sigstore", "tool"), ("gitsign", "tool"), ("OIDC", "protocol"), ("Fulcio", "service")],
     [("gitsign", "Sigstore", "IS_A"), ("gitsign", "Fulcio", "USES")],
     "how does gitsign sign commits without local keys and which Sigstore service issues the certificate",
     "sigstore gitsign oidc fulcio short lived certificate key less"),
    # --- 21 ---
    ("pre-commit hooks run locally before a commit is recorded; commit-msg hooks validate the message after; pre-push hooks gate the push itself. We use all three via the pre-commit framework.", "architecture", "technical", False,
     [("pre-commit", "concept"), ("commit-msg", "concept"), ("pre-push", "concept"), ("pre-commit framework", "tool")],
     [("pre-commit framework", "pre-commit", "USES")],
     "which three Git hook stages fire around commit and push and how do we orchestrate them",
     "git hook pre commit message push framework stage orchestrate"),
    # --- 22 ---
    (".gitignore patterns are glob-based with directory anchoring via leading slash and negation via leading bang; trailing-slash patterns match directories only, which fixed the stray file/dir ambiguity.", "fact", "technical", False,
     [(".gitignore", "file"), ("glob", "pattern"), ("negation", "concept"), ("directory anchoring", "concept")],
     [(".gitignore", "glob", "USES")],
     "how does a .gitignore pattern anchor to directories and express negation",
     "gitignore glob pattern leading slash bang negation directory"),
    # --- 23 ---
    (".gitattributes drives merge drivers, text/binary treatment, linguist language detection, and LFS filter routing; the `* text=auto eol=lf` line is what finally tamed the Windows CRLF churn.", "architecture", "technical", False,
     [(".gitattributes", "file"), ("merge driver", "concept"), ("linguist", "tool"), ("LFS", "tool"), ("CRLF", "concept")],
     [(".gitattributes", "merge driver", "CONFIGURES"), (".gitattributes", "linguist", "CONFIGURES")],
     "which behaviours does .gitattributes control and which incantation fixed the Windows line-ending churn",
     "gitattributes merge driver linguist lfs text auto eol lf crlf"),
    # --- 24 ---
    ("I keep rerere enabled globally via `rerere.enabled=true` on every dev machine; the conflict-replay win on any long-running integration rebase is worth the minor hygiene of clearing stale resolutions.", "preference", "technical", False,
     [("rerere", "tool"), ("rerere.enabled", "config"), ("rebase", "concept")],
     [("rerere", "rebase", "APPLIES_TO")],
     "why do I leave rerere enabled globally on every dev machine despite the stale-resolution hygiene cost",
     "git rerere enabled global dev conflict replay rebase hygiene"),
    # --- 25 ---
    ("`git bisect start HEAD v4.2` plus `git bisect run ./repro.sh` narrowed a perf regression to a single commit in nine steps; the script exited non-zero on the bad tick-rate measurement.", "milestone", "technical", False,
     [("git bisect", "command"), ("v4.2", "date"), ("repro.sh", "file"), ("perf regression", "error")],
     [("git bisect", "perf regression", "FIXES")],
     "how did git bisect run automate pinpointing the performance regression commit",
     "git bisect start run repro perf regression nine step automate"),
    # --- 26 ---
    ("filter-branch is deprecated in favour of git-filter-repo by Elijah Newren; filter-repo is faster, safer about refs, and doesn't choke on the forty-thousand-commit history the old tool timed out on.", "decision", "technical", False,
     [("filter-branch", "command"), ("git-filter-repo", "tool"), ("Elijah Newren", "person")],
     [("git-filter-repo", "filter-branch", "REPLACES"), ("git-filter-repo", "Elijah Newren", "AUTHORED_BY")],
     "which tool replaced filter-branch for history rewriting and who authored the successor",
     "git filter branch repo elijah newren deprecate history rewrite"),
    # --- 27 ---
    ("Chose `git filter-repo --replace-text secrets.txt` as the standard history-scrub playbook for any leaked AWS key incident, paired with a same-hour force-push to every mirror and a key rotation.", "decision", "technical", False,
     [("git filter-repo", "tool"), ("secrets.txt", "file"), ("AWS", "service"), ("force-push", "concept")],
     [("git filter-repo", "secrets.txt", "USES")],
     "how did we purge leaked AWS keys from the repo history and what mitigations ran alongside the rewrite",
     "filter repo replace text aws key purge history rotate force"),
    # --- 28 ---
    ("Git LFS hosts the heavy assets — PSDs, FBX, and game-ready meshes — while the pointer files stay in Git; `git lfs track '*.psd'` set the clean/smudge filter that swaps blobs at checkout.", "architecture", "technical", False,
     [("Git LFS", "tool"), ("pointer file", "concept"), ("clean/smudge filter", "concept"), ("git lfs track", "command"), (".psd", "file")],
     [("Git LFS", "pointer file", "USES")],
     "how does Git LFS split heavy assets from the main repo and which filter swaps blobs at checkout",
     "git lfs pointer clean smudge filter track psd large asset"),
    # --- 29 ---
    ("We picked Nx over Lerna for the TypeScript monorepo; Nx's affected-graph scheduling and remote cache shaved CI from 24 minutes to 4, and Lerna's publish flow was already showing its age.", "decision", "technical", False,
     [("Nx", "tool"), ("Lerna", "tool"), ("TypeScript", "language"), ("monorepo", "pattern"), ("remote cache", "concept")],
     [("Nx", "Lerna", "REPLACES"), ("Nx", "remote cache", "USES")],
     "which monorepo tool replaced Lerna for the TypeScript workspace and what CI win justified it",
     "nx lerna typescript monorepo affected graph remote cache ci"),
    # --- 30 ---
    ("Turborepo's pipeline config declares task dependencies and remote caching targets; `turbo run build --filter=web...` rebuilds only the web package and its downstream consumers, not the entire graph.", "fact", "technical", False,
     [("Turborepo", "tool"), ("pipeline config", "config"), ("turbo run", "command"), ("web", "project")],
     [("Turborepo", "pipeline config", "USES")],
     "how does Turborepo restrict rebuilds to one package and its downstream consumers",
     "turborepo pipeline filter web downstream cache rebuild task"),
    # --- 31 ---
    ("Bazel won the polyglot-monorepo bake-off against Pants v2; hermetic toolchains and remote execution scaled past a thousand targets where Pants's Python-first runtime started to stall.", "decision", "technical", False,
     [("Bazel", "tool"), ("Pants", "tool"), ("hermetic toolchain", "concept"), ("remote execution", "concept")],
     [("Bazel", "Pants", "PREFERS"), ("Bazel", "hermetic toolchain", "USES")],
     "why did Bazel beat Pants for the polyglot monorepo and which scaling property mattered most",
     "bazel pants hermetic toolchain remote execution polyglot monorepo"),
    # --- 32 ---
    ("GitHub's branch protection rule on main requires signed commits, a passing CI check, two approving reviews, and a linear history; the last constraint rejects merge commits from the UI merge button.", "architecture", "technical", False,
     [("GitHub", "platform"), ("branch protection", "concept"), ("main", "concept"), ("signed commits", "concept"), ("linear history", "concept")],
     [("branch protection", "main", "APPLIES_TO"), ("branch protection", "signed commits", "USES")],
     "which four gates does the GitHub branch protection rule on main enforce",
     "github branch protection main signed commit review linear history"),
    # --- 33 ---
    ("Adopted GitLab's `workflow:rules` block to gate merge-request pipeline starts in detached pipeline mode; the alternative of keeping both branch and MR pipelines active was the duplicate-pipeline trap.", "decision", "technical", False,
     [("GitLab", "platform"), ("merge-request pipeline", "concept"), ("detached pipeline", "concept"), ("workflow:rules", "config")],
     [("workflow:rules", "detached pipeline", "CONFIGURES")],
     "which GitLab config gate stopped the duplicate pipeline storm on every merge-request push",
     "gitlab ci merge request detached pipeline workflow rules gate"),
    # --- 34 ---
    ("Migrated the internal mirror from Gitea to Forgejo after the fork diverged; federation support and the community governance model lined up better with the open-infra policy.", "decision", "technical", False,
     [("Gitea", "platform"), ("Forgejo", "platform"), ("federation", "concept"), ("mirror", "infrastructure")],
     [("Forgejo", "Gitea", "REPLACES")],
     "why did the internal mirror migrate from Gitea to Forgejo after the fork",
     "gitea forgejo fork federation governance mirror migrate"),
    # --- 35 ---
    ("Bitbucket's default-reviewer rule auto-assigned the platform team to every pull request touching infrastructure/; we used that with CODEOWNERS-style gates to keep unowned changes from sneaking in.", "fact", "technical", False,
     [("Bitbucket", "platform"), ("default-reviewer", "concept"), ("pull request", "concept"), ("CODEOWNERS", "pattern"), ("infrastructure/", "file")],
     [("default-reviewer", "pull request", "APPLIES_TO")],
     "how did Bitbucket's default-reviewer rule keep unowned infrastructure changes from slipping through",
     "bitbucket default reviewer pull request codeowners infrastructure"),
    # --- 36 ---
    ("I default to a shallow clone via `git clone --depth 1` on every CI image build and deepen with `git fetch --unshallow` only when a git-describe tag is needed; shaved two minutes off every pipeline and the trade-off is rarely felt.", "preference", "technical", False,
     [("shallow clone", "concept"), ("git clone --depth 1", "command"), ("git fetch --unshallow", "command"), ("git-describe", "command")],
     [("shallow clone", "git clone --depth 1", "USES")],
     "how did shallow clone speed up CI and which command restores the full history later",
     "git shallow clone depth one fetch unshallow ci describe tag"),
    # --- 37 ---
    ("Commit SHA-1 collisions remain implausible in practice, but Git's transition to SHA-256 objects is tracked under the `objectformat` extension; we kept SHA-1 until the tooling ecosystem catches up.", "decision", "technical", False,
     [("SHA-1", "algorithm"), ("SHA-256", "algorithm"), ("objectformat", "config"), ("Git", "tool")],
     [("SHA-256", "SHA-1", "REPLACES")],
     "which hash function will replace SHA-1 for Git objects and why did we stay on SHA-1 for now",
     "git sha1 sha256 object format extension hash collision tooling"),
    # --- 38 ---
    ("`git maintenance start` schedules background prefetch, commit-graph, and incremental-repack tasks via systemd timers on Linux; pull time on the 3 GB repo dropped from 40 s to 6 s after a week of runs.", "milestone", "technical", False,
     [("git maintenance", "command"), ("commit-graph", "concept"), ("incremental-repack", "concept"), ("systemd", "tool"), ("Linux", "platform")],
     [("git maintenance", "commit-graph", "USES")],
     "which background Git maintenance tasks cut pull time on the 3 GB repo and how are they scheduled",
     "git maintenance start prefetch commit graph incremental repack systemd"),
    # --- 39 ---
    ("The commit-graph file at .git/objects/info/commit-graph caches parent and generation-number info so `git log --graph` and merge-base queries skip walking the object store for every call.", "reference", "technical", False,
     [("commit-graph", "concept"), (".git/objects/info/commit-graph", "file"), ("git log --graph", "command"), ("merge-base", "concept"), ("generation-number", "concept")],
     [("commit-graph", "generation-number", "HAS_PART")],
     "which Git cache file speeds up log and merge-base walks by storing parent generation numbers",
     "commit graph info generation number log merge base cache parent"),
    # --- 40 ---
    ("Multi-pack index (`git multi-pack-index write`) indexes all packs at once so object lookups stop linearly scanning a dozen .idx files; turned on automatically once maintenance is enabled.", "fact", "technical", False,
     [("Multi-pack index", "concept"), ("git multi-pack-index", "command"), (".idx", "file"), ("maintenance", "concept")],
     [("Multi-pack index", ".idx", "IMPROVES_ON")],
     "which index replaces scanning many .idx files and when does maintenance enable it by default",
     "git multi pack index write idx scan maintenance enable lookup"),
    # --- 41 ---
    ("Reachability bitmaps accelerate clone and fetch by precomputing the set of objects reachable from each pack's tip; `pack.writeBitmaps = true` pays off on any server-side repo with many fetchers.", "fact", "technical", False,
     [("Reachability bitmaps", "concept"), ("pack.writeBitmaps", "config"), ("clone", "concept"), ("fetch", "concept")],
     [("Reachability bitmaps", "fetch", "IMPROVES_ON")],
     "which packfile index speeds up clone and fetch on busy server-side repos",
     "git reachability bitmap pack write clone fetch server tip"),
    # --- 42 ---
    ("`git switch` and `git restore` split the overloaded `git checkout` into branch ops and file ops; onboarding docs now teach the new pair by default since the semantics are no longer context-guessed.", "preference", "technical", False,
     [("git switch", "command"), ("git restore", "command"), ("git checkout", "command")],
     [("git switch", "git checkout", "REPLACES"), ("git restore", "git checkout", "REPLACES")],
     "which two commands split the overloaded git checkout and why do the onboarding docs teach them now",
     "git switch restore checkout split branch file onboarding teach"),
    # --- 43 noise ---
    ("Someone swapped the break-room mug with an identical twin again and there's an ongoing investigation involving a fingerprint kit.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("I prefer `git pull --rebase --autostash` as the default pull behaviour on feature branches; the merge-commit clutter from a plain pull is what pushed the whole team to switch in the style guide.", "preference", "technical", False,
     [("git pull", "command"), ("--rebase", "config"), ("--autostash", "config"), ("style guide", "file")],
     [("git pull", "--rebase", "CONFIGURES")],
     "which git pull flags does the team style guide prefer on feature branches and what clutter did it cut",
     "git pull rebase autostash feature branch style guide merge clutter"),
    # --- 45 ---
    ("`core.fsmonitor` hooked into Watchman so `git status` on the 200k-file monorepo went from 7 s to 200 ms; Git asks Watchman for the changed-file set instead of stat-ing every tracked path.", "milestone", "technical", False,
     [("core.fsmonitor", "config"), ("Watchman", "tool"), ("git status", "command"), ("monorepo", "pattern")],
     [("core.fsmonitor", "Watchman", "USES")],
     "which fsmonitor integration cut git status on the 200k-file monorepo from seven seconds to a fifth of a second",
     "git fsmonitor watchman status monorepo stat changed file"),
    # --- 46 ---
    ("Protected tags in GitLab plus `push.requireSignedPush = true` stopped an impersonation attempt that force-pushed an unsigned tag; CI refused to deploy and paged on-call within a minute.", "problem", "technical", False,
     [("Protected tags", "concept"), ("push.requireSignedPush", "config"), ("GitLab", "platform"), ("impersonation", "error"), ("on-call", "concept")],
     [("Protected tags", "impersonation", "FIXES")],
     "which two Git server controls caught and blocked an unsigned tag impersonation push",
     "gitlab protected tag signed push impersonation force refuse deploy"),
    # --- 47 ---
    ("Codeowners routing in GitHub auto-requests the platform team on any PR touching terraform/; merging without their approval is blocked at the branch-protection level rather than relying on social norms.", "architecture", "technical", False,
     [("Codeowners", "pattern"), ("GitHub", "platform"), ("PR", "concept"), ("branch-protection", "concept"), ("terraform/", "file")],
     [("Codeowners", "PR", "CONFIGURES")],
     "how does Codeowners routing enforce platform-team review on terraform changes in GitHub",
     "github codeowners pull request terraform branch protection enforce"),
    # --- 48 ---
    ("`git notes add` attached a build provenance blob to each release commit without rewriting history; fetching `refs/notes/builds` is opt-in, so casual clones aren't pulling the extra objects.", "architecture", "technical", False,
     [("git notes", "command"), ("refs/notes/builds", "concept"), ("build provenance", "concept"), ("release commit", "concept")],
     [("git notes", "build provenance", "PRODUCES")],
     "how did git notes attach build provenance to release commits without rewriting any history",
     "git notes add refs notes builds provenance release commit opt in"),
    # --- 49 ---
    ("Promoted the commit-graph + multi-pack-index + reachability-bitmaps trio as the default server-side setup in the SRE playbook; 40% fewer CPU seconds per fetch on the busy mirror after rollout.", "milestone", "technical", False,
     [("commit-graph", "concept"), ("multi-pack-index", "concept"), ("reachability-bitmaps", "concept"), ("SRE playbook", "file"), ("mirror", "infrastructure")],
     [("commit-graph", "mirror", "DEPLOYED_ON"), ("reachability-bitmaps", "mirror", "DEPLOYED_ON")],
     "which three server-side Git acceleration features became the SRE playbook default and what CPU win landed",
     "commit graph multi pack reachability bitmap sre playbook mirror cpu"),
    # --- 50 ---
    ("Cross-forge mirroring from GitHub to Gitea uses `git push --mirror` from a cron job on a runner; the runner holds a scoped PAT, and failures page via the same alert route as the CI pipeline.", "architecture", "technical", False,
     [("GitHub", "platform"), ("Gitea", "platform"), ("git push --mirror", "command"), ("cron", "tool"), ("PAT", "concept"), ("runner", "infrastructure")],
     [("git push --mirror", "Gitea", "COMMUNICATES_WITH"), ("runner", "cron", "USES")],
     "how is the GitHub-to-Gitea mirror scheduled and authenticated on the runner",
     "github gitea git push mirror cron runner pat alert route"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
