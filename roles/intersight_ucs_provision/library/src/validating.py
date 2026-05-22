"""Validation helpers for Intersight UCS provisioning inputs."""
# =============================================================================
# Source Modules
# =============================================================================
import sys


def pr_red(skk):
    """Print text in red to stdout."""
    print(f"\033[91m {skk}\033[00m")


try:
    import re
    import validators
except ImportError as e:
    pr_red(f'src/validating.py line 9 - !!! ERROR !!!\n{e.__class__.__name__}')
    pr_red(f" Module {e.name} is required to run this script")
    pr_red(f" Install the module using the following: `pip install {e.name}`")
    sys.exit(1)

# =============================================================================
# Validation Functions
# =============================================================================


def dns_name(var_name, var_value):  # pylint: disable=invalid-name
    """Return True when var_value is a valid DNS hostname, False otherwise."""
    hostname = var_value
    valid_count = 0
    if len(hostname) > 255:
        valid_count += 1
    if not validators.domain(hostname):
        valid_count += 1
    if hostname[-1] == ".":
        # strip exactly one dot from the right, if present
        hostname = hostname[:-1]
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    if not all(allowed.match(x) for x in hostname.split(".")):
        valid_count += 1
    if not valid_count == 0:
        print('-' * 108)
        print(f'   Error with {var_name}.  "{var_value}" is not a valid Hostname/Domain.')
        print('   Confirm that you have entered the DNS Name Correctly.')
        print('-' * 108)
        return False
    return True


def ip_address(var_name, var_value):  # pylint: disable=invalid-name
    """Return True when var_value is a valid IPv4 or IPv6 address, False otherwise."""
    if re.search('/', var_value):
        x = var_value.split('/')
        address = x[0]
    else:
        address = var_value
    valid_count = 0
    if re.search(r'\.', address):
        if not validators.ip_address.ipv4(address):
            valid_count += 1
    else:
        if not validators.ip_address.ipv6(address):
            valid_count += 1
    if not valid_count == 0 and re.search(r'\.', address):
        print('-' * 108)
        print(f'   Error with {var_name}. "{var_value}" is not a valid IPv4 Address.')
        print('-' * 108)
        return False
    if not valid_count == 0:
        print('-' * 108)
        print(f'   Error with {var_name}. "{var_value}" is not a valid IPv6 Address.')
        print('-' * 108)
        return False
    return True
