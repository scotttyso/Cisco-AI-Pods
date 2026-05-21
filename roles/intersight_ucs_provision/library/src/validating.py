#=============================================================================
# Source Modules
#=============================================================================
def prRed(skk): print("\033[91m {}\033[00m" .format(skk))
import sys
try:
    import re, validators
except ImportError as e:
    prRed(f'src/validating.py line 9 - !!! ERROR !!!\n{e.__class__.__name__}')
    prRed(f" Module {e.name} is required to run this script")
    prRed(f" Install the module using the following: `pip install {e.name}`")
    sys.exit(1)

#=============================================================================
# Validation Functions
#=============================================================================
def dns_name(varName, varValue):
    hostname = varValue
    valid_count = 0
    if len(hostname) > 255: valid_count += 1
    if not validators.domain(hostname): valid_count += 1
    if hostname[-1] == ".": hostname = hostname[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    if not all(allowed.match(x) for x in hostname.split(".")): valid_count += 1
    if not valid_count == 0:
        print(f'{"-"*108}')
        print(f'   Error with {varName}.  "{varValue}" is not a valid Hostname/Domain.')
        print(f'   Confirm that you have entered the DNS Name Correctly.')
        print(f'{"-"*108}')
        return False
    else: return True

def ip_address(varName, varValue):
    if re.search('/', varValue):
        x = varValue.split('/')
        address = x[0]
    else: address = varValue
    valid_count = 0
    if re.search(r'\.', address):
        if not validators.ip_address.ipv4(address): valid_count += 1
    else:
        if not validators.ip_address.ipv6(address): valid_count += 1
    if not valid_count == 0 and re.search(r'\.', address):
        print(f'{"-"*108}')
        print(f'   Error with {varName}. "{varValue}" is not a valid IPv4 Address.')
        print(f'{"-"*108}')
        return False
    elif not valid_count == 0:
        print(f'{"-"*108}')
        print(f'   Error with {varName}. "{varValue}" is not a valid IPv6 Address.')
        print(f'{"-"*108}')
        return False
    else: return True
