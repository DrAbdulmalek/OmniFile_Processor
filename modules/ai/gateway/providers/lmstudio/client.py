"""LM Studio provider implementation."""

from ..anthropic_messages import AnthropicMessagesTransport
from ..base import ProviderConfig
from ..defaults import LMSTUDIO_DEFAULT_BASE


class LMStudioProvider(AnthropicMessagesTransport):
    """LM Studio provider using native Anthropic Messages endpoint."""

    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            provider_name="LMSTUDIO",
            default_base_url=LMSTUDIO_DEFAULT_BASE,
        )
