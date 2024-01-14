import xmlrpc.client

# Replace these with your Odoo server details
url = 'http://13.49.59.166:80'  # Correct URL
db = 'KMNSS'
username = 'odoo'
password = 'sugam@kmnss!23#'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Replace these with your target date range
target_date_start = '2027-10-01'
target_date_end = '2027-10-31'

try:
    # Call the getbalance method with both date range parameters
    balances = models.execute_kw(
        db,
        uid,
        password,
        'account.account',
        'getbalance',
        [target_date_start, target_date_end],  # Pass both date range parameters
        {}
    )

    # Print the balances with account ID, balance
    for account_id, balance in balances.items():
        print(f"Account ID: {account_id}")
        print(f"Balance: {balance}")
        print("")

except xmlrpc.client.Fault as err:
    print(f"XML-RPC Fault: {err}")
except Exception as e:
    print(f"An error occurred: {e}")
