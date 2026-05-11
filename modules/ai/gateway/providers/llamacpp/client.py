"""Llama.cpp provider implementation."""

from ..anthropic_messages import AnthropicMessagesTransport
from ..base import ProviderConfig
from ..defaults import LLAMACPP_DEFAULT_BASE


class LlamaCppProvider(AnthropicMessagesTransport):
    """Llama.cpp provider using native Anthropic Messages endpoint."""

    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            provider_name="LLAMACPP",
            default_base_url=LLAMACPP_DEFAULT_BASE,
        )
