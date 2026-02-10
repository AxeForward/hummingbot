from decimal import Decimal
from typing import Optional

from pydantic import ConfigDict, Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

# Maker rebates(-0.02%) are paid out continuously on each trade directly to the trading wallet.(https://paradex.gitbook.io/paradex-docs/trading/fees)
DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("-0.00005"),
    taker_percent_fee_decimal=Decimal("0.0003"),
    buy_percent_fee_deducted_from_returns=True
)

CENTRALIZED = True
EXAMPLE_PAIR = "BTC-USD"
BROKER_ID = "HBOT"


def validate_bool(value: str) -> Optional[str]:
    """
    Permissively interpret a string as a boolean
    """
    valid_values = ('true', 'yes', 'y', 'false', 'no', 'n')
    if value.lower() not in valid_values:
        return f"Invalid value, please choose value from {valid_values}"


class ParadexPerpetualConfigMap(BaseConnectorConfigMap):
    connector: str = "paradex_perpetual"
    paradex_perpetual_l1_address: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your L1 Address",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    paradex_perpetual_is_testnet: bool = Field(
        default=False,
        json_schema_extra={
            "prompt": "Use testnet? (True/False)",
            "is_secure": False,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    paradex_perpetual_l1_private_key: Optional[SecretStr] = Field(
        default=None,
        json_schema_extra={
            "prompt": "Enter your L1 private key",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    paradex_perpetual_l2_private_key: Optional[SecretStr] = Field(
        default=None,
        json_schema_extra={
            "prompt": "Enter your L2 private key",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )


KEYS = ParadexPerpetualConfigMap.model_construct()



OTHER_DOMAINS = ["paradex_perpetual_testnet"]
OTHER_DOMAINS_PARAMETER = {
    "paradex_perpetual_testnet": "paradex_perpetual_testnet",
}
OTHER_DOMAINS_EXAMPLE_PAIR = {
    "paradex_perpetual_testnet": EXAMPLE_PAIR,
}
OTHER_DOMAINS_DEFAULT_FEES = {
    "paradex_perpetual_testnet": [0, 0.025],
}

class ParadexPerpetualTestnetConfigMap(BaseConnectorConfigMap):
    connector: str = "paradex_perpetual_testnet"
    paradex_perpetual_l1_address: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your L1 Address",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    paradex_perpetual_is_testnet: bool = Field(
        default=True,
        json_schema_extra={"is_connect_key": True}
    )
    paradex_perpetual_l1_private_key: Optional[SecretStr] = Field(
        default=None,
        json_schema_extra={
            "prompt": "Enter your L1 private key",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    paradex_perpetual_l2_private_key: Optional[SecretStr] = Field(
        default=None,
        json_schema_extra={
            "prompt": "Enter your L2 private key",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    model_config = ConfigDict(title="paradex_perpetual")


OTHER_DOMAINS_KEYS = {
    "paradex_perpetual_testnet": ParadexPerpetualTestnetConfigMap.model_construct(),
}
