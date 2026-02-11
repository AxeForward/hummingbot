import logging
from typing import Optional

from paradex_py.account.account import ParadexAccount
from paradex_py.api.api_client import ParadexApiClient
from paradex_py.environment import PROD, TESTNET
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTRequest, WSRequest

logger = logging.getLogger(__name__)


class ParadexPerpetualAuth(AuthBase):
    """
    Auth class required by Paradex Perpetual API
    """
    def __init__(
        self,
        paradex_perpetual_l1_address: str,
        paradex_perpetual_is_testnet: bool,
        paradex_perpetual_l1_private_key: Optional[str] = None,
        paradex_perpetual_l2_private_key: Optional[str] = None
    ):
        self._paradex_perpetual_l1_address = paradex_perpetual_l1_address
        self._paradex_perpetual_chain = TESTNET if paradex_perpetual_is_testnet else PROD
        self._paradex_perpetual_l1_private_key = paradex_perpetual_l1_private_key
        self._paradex_perpetual_l2_private_key = paradex_perpetual_l2_private_key

        self._paradex_account: ParadexAccount = None
        self._rest_api_client: ParadexApiClient = None

    @property
    def paradex_account(self):
        if self._paradex_account is None:
            self.paradex_rest_client
        return self._paradex_account

    @property
    def paradex_rest_client(self):
        if self._rest_api_client is None:

            env = self._paradex_perpetual_chain

            self._rest_api_client = ParadexApiClient(
                env=env,
                logger=None
            )
            self.config = self._rest_api_client.fetch_system_config()
            self._paradex_account = ParadexAccount(
                config=self.config,
                l1_address=self._paradex_perpetual_l1_address,
                l1_private_key=self._paradex_perpetual_l1_private_key,
                l2_private_key=self._paradex_perpetual_l2_private_key
            )

            try:
                self._rest_api_client.init_account(self._paradex_account)
            except Exception as e:
                if "NOT_ONBOARDED" in str(e).upper():
                    if self._paradex_perpetual_l1_private_key:
                        logger.info("Paradex account not onboarded. Calling onboarding endpoint...")
                        try:
                            self._rest_api_client.onboarding()
                        except Exception as onboard_err:
                            if "PARENT_ADDRESS_ALREADY_ONBOARDED" in str(onboard_err).upper():
                                raise ValueError(
                                    "Your L1 address is already registered on Paradex with a different L2 account. "
                                    "Make sure the L2 private key matches the one used when you first onboarded. "
                                    "Leave the L2 private key empty to auto-derive it from your L1 private key."
                                ) from onboard_err
                            raise
                        self._rest_api_client.init_account(self._paradex_account)
                    else:
                        logger.error("Paradex account is not onboarded and no L1 private key was provided to onboard.")
                        raise
                else:
                    raise

        return self._rest_api_client

    @property
    def jwt_token(self):
        """Get JWT token from the authenticated rest client headers."""
        auth_header = self.paradex_rest_client.client.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return ""

    async def rest_authenticate(self, request: RESTRequest) -> RESTRequest:
        self.paradex_rest_client._validate_auth()

        headers = self.paradex_rest_client.client.headers

        if request.headers is not None:
            headers.update(request.headers)

        request.headers = headers
        return request

    async def ws_authenticate(self, request: WSRequest) -> WSRequest:
        return request
