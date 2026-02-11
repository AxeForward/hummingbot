import asyncio

try:
    from paradex_py import ParadexSubkey
except Exception:
    ParadexSubkey = None

try:
    from eth_account import Account as EthAccount
except Exception:
    EthAccount = None

from paradex_py.account.account import ParadexAccount
from paradex_py.api.api_client import ParadexApiClient
from paradex_py.environment import PROD

# ── Fill in your credentials ────────────────────────────────────────────────
CONFIG = {
    "l1_address":     "L1 Public Key",
    "l1_private_key": "L1 Private Key",
    "l2_private_key": "L2 Private Key",
    "l2_address":     "L2 Public Key",
}
# ────────────────────────────────────────────────────────────────────────────

RESULTS: dict[str, str] = {}


def normalize_l2_hex(addr: str) -> str:
    v = addr.lower().strip()
    if v.startswith("0x"):
        v = v[2:]
    return hex(int(v, 16))


def section(title: str):
    print(f"\n{title}")
    print("-" * 80)


def _make_client_and_config():
    client = ParadexApiClient(env=PROD, logger=None)
    config = client.fetch_system_config()
    return client, config


# ── Test 1: manual L2 key only (no L1 private key) ──────────────────────────
async def test_manual_l2():
    section("Test 1: Manual L2 private key  (no L1 private key)")
    try:
        client, config = _make_client_and_config()
        account = ParadexAccount(
            config=config,
            l1_address=CONFIG["l1_address"],
            l2_private_key=CONFIG["l2_private_key"],
        )
        client.account = account

        sdk_l2_addr = f"0x{account.l2_address:064x}"
        print(f"  L2 address from SDK : {sdk_l2_addr}")
        print(f"  L2 address from UI  : {CONFIG['l2_address']}")
        if normalize_l2_hex(sdk_l2_addr) != normalize_l2_hex(CONFIG["l2_address"]):
            print("  X  L2 address mismatch — check CONFIG['l2_address']")
        else:
            print("  OK L2 address matches")

        print("  Calling auth()...")
        client.auth()
        print("  OK auth success — this manual L2 key IS the registered account")
        RESULTS["test1"] = "OK"
    except Exception as e:
        msg = str(e)
        if "NOT_ONBOARDED" in msg.upper():
            print("  X  auth failed: this L2 key is NOT the registered account")
            RESULTS["test1"] = "FAIL_NOT_ONBOARDED"
        else:
            print(f"  X  failed: {e}")
            RESULTS["test1"] = f"FAIL: {e}"


# ── Test 2: L2 derived from L1 private key ───────────────────────────────────
async def test_derived_from_l1():
    section("Test 2: L2 derived from L1 private key  (SDK standard derivation)")
    try:
        client, config = _make_client_and_config()
        account = ParadexAccount(
            config=config,
            l1_address=CONFIG["l1_address"],
            l1_private_key=CONFIG["l1_private_key"],
            # l2_private_key intentionally omitted → SDK derives it from L1
        )
        client.account = account

        derived_l2_priv = f"0x{account.l2_private_key:064x}"
        derived_l2_addr = f"0x{account.l2_address:064x}"

        print(f"  Derived L2 private key : {derived_l2_priv}")
        print(f"  Manual  L2 private key : {CONFIG['l2_private_key']}")
        if normalize_l2_hex(derived_l2_priv) == normalize_l2_hex(CONFIG["l2_private_key"]):
            print("  OK Keys match — both Tests 1 and 2 should behave the same")
        else:
            print("  INFO Keys differ — Paradex is registered with exactly one of them")

        print(f"\n  Derived L2 address : {derived_l2_addr}")
        print(f"  Manual  L2 address : {CONFIG['l2_address']}")

        print("  Calling auth()...")
        client.auth()
        print("  OK auth success — derived L2 key IS the registered account")
        print("  → In hummingbot: provide L1 private key and leave L2 private key EMPTY")
        RESULTS["test2"] = "OK"
    except Exception as e:
        msg = str(e)
        if "NOT_ONBOARDED" in msg.upper():
            print("  X  auth failed: derived L2 key is NOT the registered account")
            print("  → The account was not registered with the standard MetaMask derivation")
            RESULTS["test2"] = "FAIL_NOT_ONBOARDED"
        else:
            print(f"  X  failed: {e}")
            RESULTS["test2"] = f"FAIL: {e}"


# ── Test 3: L2-only via ParadexSubkey (README recommended for L2-only) ───────
async def test_subkey_l2_only():
    section("Test 3: L2-only via ParadexSubkey  (README recommended method)")
    if ParadexSubkey is None:
        print("  X ParadexSubkey not available in installed paradex_py version")
        RESULTS["test3"] = "UNAVAILABLE"
        return

    try:
        paradex = ParadexSubkey(
            env=PROD,
            l2_private_key=CONFIG["l2_private_key"],
            l2_address=CONFIG["l2_address"],
        )
        await paradex.init_account()
        print("  OK ParadexSubkey.init_account() succeeded")

        account_addr = None
        if hasattr(paradex.api_client, "fetch_account_info"):
            info = paradex.api_client.fetch_account_info()
            account_addr = info.get("account")
        elif hasattr(paradex.api_client, "fetch_account_summary"):
            summary = paradex.api_client.fetch_account_summary()
            account_addr = getattr(summary, "account", None)

        if account_addr:
            print(f"  Account address : {account_addr}")
            print("  OK L2-only Subkey auth works — this L2 key is the registered account")
            print("  → In hummingbot: provide this L2 private key + L2 address; no L1 needed")
            RESULTS["test3"] = "OK"
        else:
            print("  INFO init succeeded but account endpoint returned empty address")
            RESULTS["test3"] = "OK_NO_ADDR"
    except Exception as e:
        msg = str(e)
        if "NOT_ONBOARDED" in msg.upper():
            print("  X  L2-only auth failed: this L2 key is NOT the registered account")
            RESULTS["test3"] = "FAIL_NOT_ONBOARDED"
        else:
            print(f"  X  failed: {e}")
            RESULTS["test3"] = f"FAIL: {e}"


# ── Summary ──────────────────────────────────────────────────────────────────
def print_summary():
    section("Summary & hummingbot connect recommendation")
    t1 = RESULTS.get("test1", "?")
    t2 = RESULTS.get("test2", "?")
    t3 = RESULTS.get("test3", "?")

    if t1 == "OK":
        print("  Test 1 OK → manual L2 key is valid.")
        print("  hummingbot: enter L1 address, leave L1 key EMPTY, enter manual L2 key")
        print("  WARNING: if L1 key is also provided, SDK silently ignores L2 key (l1 wins)!")
    if t2 == "OK":
        print("  Test 2 OK → L1-derived L2 key is valid.")
        print("  hummingbot: enter L1 address + L1 key, leave L2 EMPTY")
    if t3 == "OK":
        print("  Test 3 OK → L2-only Subkey auth is valid.")
        print("  hummingbot: enter L1 address + manual L2 key, leave L1 private key EMPTY")

    if t1 != "OK" and t2 != "OK" and t3 not in ("OK", "OK_NO_ADDR"):
        print("  All tests failed:")
        print("   • If L1 address is wrong → this address has no Paradex account")
        print("   • If L1 private key is wrong → derived L2 will also be wrong")
        print("   • If L2 key was from a hardware wallet → provide the exact exported L2 key")

    if t3 == "UNAVAILABLE":
        print("  NOTE: paradex_py version does not ship ParadexSubkey.")
        print("        L2-only auth requires a newer version.")


def test_l1_key_ownership():
    """Verify that CONFIG['l1_private_key'] actually owns CONFIG['l1_address']."""
    section("Pre-check: L1 private key → L1 address correspondence")
    if EthAccount is None:
        print("  INFO eth_account not available, skipping L1 ownership check")
        return
    l1_key = CONFIG["l1_private_key"]
    if not l1_key.startswith("0x"):
        l1_key = "0x" + l1_key
    derived_address = EthAccount.from_key(l1_key).address
    expected_address = CONFIG["l1_address"]
    print(f"  Address derived from L1 key : {derived_address}")
    print(f"  Address in CONFIG           : {expected_address}")
    if derived_address.lower() == expected_address.lower():
        print("  OK L1 private key matches L1 address")
        RESULTS["l1_ownership"] = "OK"
    else:
        print("  X  MISMATCH — the L1 private key does NOT belong to this L1 address!")
        print("     This explains why the SDK-derived L2 key is different.")
        print("     The EIP-712 signing uses the wrong key, so a different L2 is produced.")
        RESULTS["l1_ownership"] = "MISMATCH"


async def main():
    print("Paradex key diagnosis")
    print("=" * 80)
    print(f"L1 Address : {CONFIG['l1_address']}")
    print(f"L2 Address : {CONFIG['l2_address']}")

    test_l1_key_ownership()
    await test_manual_l2()
    await test_derived_from_l1()
    await test_subkey_l2_only()
    print_summary()


if __name__ == "__main__":
    asyncio.run(main())
