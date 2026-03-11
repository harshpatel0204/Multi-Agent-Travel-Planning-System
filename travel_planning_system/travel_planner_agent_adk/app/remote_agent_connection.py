"""Remote agent connection for A2A communication."""

from a2a.client import A2AClient
from a2a.types import AgentCard


class RemoteAgentConnections:
    """Manages connections to remote agents."""

    def __init__(self, agent_card: AgentCard = None, agent_url: str = None, httpx_client = None):
        """Initialize the remote agent connection."""
        if not agent_card and not agent_url:
            raise ValueError("Must provide either agent_card or url")
        
        self.agent_card = agent_card
        self.agent_url = agent_url
        
        if agent_url and httpx_client:
            self.client = A2AClient(httpx_client=httpx_client, url=agent_url, agent_card=agent_card)
        else:
            self.client = None

    async def send_message(self, message_request):
        """Send a message to the remote agent."""
        return await self.client.send_message(message_request)