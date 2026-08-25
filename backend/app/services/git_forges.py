"""Per-forge quirks for git credentials — one row per provider, like ``llm_quirks``.

Every vendor difference a git account touches lives here: the API base a token
is verified against, the field its identity comes back in, the scope header, and
the username git wants in front of the token in a clone URL. No call site may
compare ``provider`` to a vendor name; ask this table instead.
"""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_PROVIDER = "github"


@dataclass(frozen=True)
class ForgeQuirks:
    provider: str
    label: str
    default_host: str
    #: Username git expects ahead of the token in an authenticated clone URL.
    #: GitHub reads any username and takes the token as the password, but
    #: GitLab only accepts these two spellings, so the value is not cosmetic.
    git_username: str
    #: ``{host}`` is substituted with the account's host.
    api_base_template: str
    #: Same, for a host that is not the vendor's own (an Enterprise install).
    self_hosted_api_base_template: str
    #: Path appended to the API base to resolve the token's own identity.
    identity_path: str
    #: Key in the identity response holding the account name.
    identity_field: str
    #: Response header listing granted scopes, when the vendor sends one.
    scope_header: str | None
    auth_header: str
    auth_value_template: str


FORGES: dict[str, ForgeQuirks] = {
    "github": ForgeQuirks(
        provider="github",
        label="GitHub",
        default_host="github.com",
        git_username="x-access-token",
        api_base_template="https://api.{host}",
        self_hosted_api_base_template="https://{host}/api/v3",
        identity_path="/user",
        identity_field="login",
        scope_header="x-oauth-scopes",
        auth_header="Authorization",
        auth_value_template="Bearer {token}",
    ),
    "gitlab": ForgeQuirks(
        provider="gitlab",
        label="GitLab",
        default_host="gitlab.com",
        git_username="oauth2",
        api_base_template="https://{host}/api/v4",
        self_hosted_api_base_template="https://{host}/api/v4",
        identity_path="/user",
        identity_field="username",
        # GitLab reports scopes only on the token-introspection endpoint, which
        # a plain PAT cannot always reach; leave the column null rather than
        # spend a second call on a field nothing gates on.
        scope_header=None,
        auth_header="Authorization",
        auth_value_template="Bearer {token}",
    ),
}

#: Providers that carry no credential at all. ``local`` repos are on disk and
#: a bare ``git`` URL is anonymous, so neither can hold an account.
CREDENTIAL_FREE_PROVIDERS = frozenset({"local"})


def get_forge(provider: str) -> ForgeQuirks:
    forge = FORGES.get(provider)
    if forge is None:
        raise ValueError(
            f"unknown git provider {provider!r}; expected one of {sorted(FORGES)}"
        )
    return forge


def api_base(provider: str, host: str) -> str:
    forge = get_forge(provider)
    template = (
        forge.api_base_template
        if host == forge.default_host
        else forge.self_hosted_api_base_template
    )
    return template.format(host=host)
