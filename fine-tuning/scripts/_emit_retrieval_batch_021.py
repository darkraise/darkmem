"""One-off emitter for retrieval top-up batch-021 (typo-kind queries).

Reads shared rows at 0-indexed line offsets 2000..2099 from
`data/v2/shared/shared.jsonl` and emits one retrieval top-up row per
source with a short, plausibly-misspelled query. Output is written to
`data/v2/retrieval/batch_021.tmp.jsonl` with ids ret-02001..02100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_021.tmp.jsonl"

ID_OFFSET = 2000
SHARED_OFFSET = 2000
QUERY_KIND = "typo"

# One typo-kind query per source row (100 entries, matching shared lines 2000..2099).
# Each query contains 1-3 realistic typos across content words and stays readable.
QUERIES: list[str] = [
    "helix multicurser and tree-siter textobjects replcaed three nvim plugns",  # 02001
    "which python langauge server swapd from pyright for stricter defualts",  # 02002
    "jedi langauge servr still right for legcy python 2.7 poskets",  # 02003
    "neovim packr to lazy nvim migraton droped startup to 28 ms",  # 02004
    "vscode worspace settings shold only hold projet scoped overides",  # 02005
    "jetbrains gatway thin clent dev contaner on build box memry",  # 02006
    "jetbrains toolbox synk keeps sdk paths and kemap across machines",  # 02007
    "zed multiplayr editing tsted in incidnet review runbook two engneers",  # 02008
    "team-wide fish adption stalled posix gap broke copy paste stakoverflow",  # 02009
    "ran out of cofee aginn time to ordr next bag",  # 02010
    "replced oh-my-zsh with starhip 2026-02-05 promt rendr 140 to 8 ms",  # 02011
    "atuin shell histoy sync made ctrl-r expereince span machnies e2e encrpted",  # 02012
    "fzf ctrl-t interctive file pickng ctrl-g git tracked fils binding",  # 02013
    "tmux to zelij migraton discoverble keybindng bar helps new hres",  # 02014
    "direnv per repo envrc kept secrets out of shll rc use_flake nix",  # 02015
    "consolidte asdf rbenv nvm onto mise singl tool versions file",  # 02016
    "proto handls rust toolchan swaps beter than mise on aple silcon",  # 02017
    "pre-comit hooks precommit config yml run same ruff mypy as ci",  # 02018
    "chezmoi beat yadm and bare git dotfile strategis templatd host sectons",  # 02019
    "brewfile snapsht gave reproduible macos base brew bundl dump diff",  # 02020
    "wezterm lua confg per-domain launch profils color ssh hsts prod typos",  # 02021
    "alacritty stayed on low spec boxes 60fps on pi4 cluser dashbord",  # 02022
    "ghosty adpton fst on macos side native framwork zero tearing 4k",  # 02023
    "warp ai side panl copy paste short but tmux copy mod brakes",  # 02024
    "ssh proxyjump replced nestd ssh-t patern for bation hops",  # 02025
    "ssh_config match exc swaps identityfile insde vpn depoy key unreach",  # 02026
    "gh extnsion model let us instal gh-dash gh-copilto without poluting path",  # 02027
    "lazygit plus gh-dash our defalt git ui bets intelij git panel",  # 02028
    "delta turns git pagr into syntax-highlited side by side .gitconig core.pger",  # 02029
    "reched for gron when jq expresion got deep flaten json greppble",  # 02030
    "yq reds yaml with jq style expresions replaced sed in kustmize edits",  # 02031
    "centralisng ripgrep defalts in ripgreprc smart-case hiden stopped wrapers",  # 02032
    "fd deflt ignores gitignore plus hiden files replces find not path",  # 02033
    "eza replced lsd on half team machines git-stats col per row",  # 02034
    "ssh_config include directves split 400 line file into per-accont fragmnts",  # 02035
    "mise taks replced makefile on sampl repo mise.toml check runs lint tst",  # 02036
    "zed languge srver reuse broke python monorepo each worktre basdpyright memry",  # 02037
    "neovim buit-in lsp caught up with coc.nvim on completon ergonmics",  # 02038
    "ideavim keymps cover 90 precent of vim mucle memry in intelij",  # 02039
    "sublime text 4 stil boots under 300ms on ancint buid servr log tail",  # 02040
    "bat pags source fils with sytnax highlightng and git blme gutrs",  # 02041
    "zoxide replced z script on everones dotfils rust rewrte respect xdg",  # 02042
    "nushel adpton still experiental love strutured pipelins posix scrpts opt-in",  # 02043
    "gh copilto suggst saves man-pge round trip for obscre tar flgs",  # 02044
    "warp plus tmux garbld 256 clor nestd ssh swtched to ghostty or kity",  # 02045
    "neovim tree-sitr textobjcts unlok fst refctors vaf selct daf delte",  # 02046
    "neovim spel check to medcal dictonary plus projet glosary via spelfile",  # 02047
    "thinkpad x1 specifc ssh_config host forses usekechain yes on macos",  # 02048
    "git-absrb chged stacked diff revew loop sprads wip edits to ancster",  # 02049
    "kept emcs on exactly one worksation for orgmode planng weekly revew notes",  # 02050
    "switchd publc lst endpoints from ofset to cusor baed paginaton opaque",  # 02051
    "paymnts post endpont accepts idempotncy key hedar duplcate 24h 201 reply",  # 02052
    "renmed rate limt hedrs from x-ratelimit to rfc 9156 ratelmit form",  # 02053
    "adoped rfc 7807 problm+json for all 4xx 5xx bodys type uri stble errcode",  # 02054
    "added expnd qury param for opt-in feld expnsion on invoice resposes",  # 02055
    "rejcted json api for publc intrface included arry linkge shape sdk normalsr",  # 02056
    "spars feldsets fields= cut moble payloads 60% on timline strict rejt",  # 02057
    "strming reponses went sse insted of websoket for completons proxy auth",  # 02058
    "sdk retry polcy jiterred exponetial bakoff capd 30s four atmpts 408 429",  # 02059
    "cofee machne in kitchn back to beping at randm intervls aginn",  # 02060
    "marked /v1/chrges endpoint with deprecaton and sunsett hedrs 2026-10-01",  # 02061
    "versioning moved to stripe style date pining api-verson hedar path /v1 freze",  # 02062
    "rejcted accpet hedar contnet negotaton for versonng cdn cachd wrong",  # 02063
    "webhok signatres rotate throug keyset rather than sigle secrt verify multi",  # 02064
    "webhok replay protcton five-min timstamp window plus 24h redis dedup",  # 02065
    "cursor paginaton consistnt under deltes cursor encods create_at id snaphsot",  # 02066
    "patch endpoits accpt json merg patch by defalt array reorder via json patch",  # 02067
    "froze spec at openapi 3.1 despte toolng gaps json schma alinment codgen",  # 02068
    "hand rolld sdks for pyton and typescrpt generated clents for go ruby jva php",  # 02069
    "generted go clent used poinr heavy optinal fields post processr to null wrapr",  # 02070
    "publc sdk constructrs take optins bag insted of positionl args telmetry hook",  # 02071
    "clents chain midleware in requst order responce revese interceptr exlicit list",  # 02072
    "addd telmetry hook intrface so hosts plug in logging or mtrics no-op defalt",  # 02073
    "responses emit cache-contrl stale-while-revalidte 60 on gts backgrund refrsh",  # 02074
    "enbled servr timng on every resposne sdk surfce brkdown via telmetry hook",  # 02075
    "sdks injct tracparent and trcestate on evry outbound reqst opentelmetry contxt",  # 02076
    "strming sse resposes wrap evnts in sealed envlope with type and seq last-event-id",  # 02077
    "pyton sdk expses both sync and asynk clients sam packge blesed async path asyncio",  # 02078
    "paginaton helpers in sdks retun asyncitrator objcts for lops cursor threding backpresur",  # 02079
    "error clases miror problem json type hierarchy conflicterr retry_aftr feld",  # 02080
    "removd positonal args from new public methds on 2026-03-05 keywrd only signtures",  # 02081
    "kept java sdk on buildr pattrn for requst constrction idiom ide autocmplete chain",  # 02082
    "documnted sdk stabilty tiers stble previw experimetal _previw subpackge brak",  # 02083
    "nevr reuse remvd field name insde same api versoin status rebrnd taut us",  # 02084
    "sdks expse raw_reponse proprty on evry return objct headrs status reqst id",  # 02085
    "requst ids echod from x-reqest-id hedr into evry errr objct suport runbok",  # 02086
    "adopted aditive json evoltion only new fields optnal enms extensble unknwn preserv",  # 02087
    "publc enms ar open sts sdks unkown variants deserailse typed unkown str wrapr",  # 02088
    "timouts split into conect read and totl on http clent tls hanshake budgt",  # 02089
    "user-agnt built from sdk name sdk versoin langage versoin and os dashbords spot",  # 02090
    "conditonal reqsts work throug etag and if-none-mtch 304 in sdk hidden",  # 02091
    "spars updte conficts retun 409 with problem json currnt_versoin expcted_versoin optmistic lock",  # 02092
    "docs publsh publc deprecaton polcy 180 dys notce changlog hedr usge reprts",  # 02093
    "long runing operaions retun 202 operation-locaton hedar sdk hidds polling retry-aftr",  # 02094
    "bulk endpoits accpt partal sucess respose body per-item stats typed bulkresut sublists",  # 02095
    "evry respose carys x-idempotncy-replayd hedar when key matched prir reqst",  # 02096
    "sdk publishng pipline enfrces semver rules via golden diff chck against pror minor",  # 02097
    "droped accept applictn vnd api json contet type after json api rewrte abondned",  # 02098
    "capablity discvery via get wel-known api-capabiltes enumertes enbled featres sdk caches",  # 02099
    "evry sdk ships single lne mock transpot for tests swapng requres one ctor arg",  # 02100
]


def _load_sources() -> list[dict]:
    with SHARED.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    slice_ = lines[SHARED_OFFSET:SHARED_OFFSET + 100]
    return [json.loads(line) for line in slice_]


def emit() -> int:
    if len(QUERIES) != 100:
        raise ValueError(f"expected 100 queries, got {len(QUERIES)}")
    sources = _load_sources()
    if len(sources) != 100:
        raise ValueError(f"expected 100 source rows at offset {SHARED_OFFSET}, got {len(sources)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (src, query) in enumerate(zip(sources, QUERIES), start=1):
            word_count = len(query.split())
            if not (4 <= word_count <= 18):
                raise ValueError(f"query {i} has {word_count} words, out of 4-18 range: {query!r}")
            row = {
                "id": f"ret-{ID_OFFSET + i:05d}",
                "source_id": src["id"],
                "query": query,
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
