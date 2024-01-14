import xmlrpc.client

# Replace these with your Odoo server details
url = 'http://13.49.59.166:8069'
db = 'KMNSS'
username = 'sugam.pandey@gmail.com'
password = 'sugam@kmnss!23#'

# Create XML-RPC server proxies for common and models
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Replace these with your target date range
target_date_start = '2020-10-01'
target_date_end = '2027-10-31'

try:
    # Authenticate and get user ID
    uid = common.authenticate(db, username, password, {})

    # Call the getbalance method with both date range parameters
    balances = models.execute_kw(
        db,
        uid,
        password,
        'account.account',
        'getbalance',
        [target_date_start, target_date_end],
        {}
    )

    # Initialize the total balance variable
    total_balance = 0.0

    # Check if balances is a list and not empty
    if isinstance(balances, list) and balances:
        for balance in balances:
            # Access and print the fields from the dictionary
            print(f"Account ID: {balance['account_id']}")
            print(f"Account Name: {balance['account_name']}")
            print(f"Root ID: {balance['root_id']}")
            print(f"Date: {balance['date']}")
            print(f"Balance: {balance['balance']}")
            print("")

            # Add the balance to the total balance
            total_balance += balance['balance']

        # Print the total balance
        print(f"Total Balance: {total_balance}")

    else:
        print("No balances found.")

except xmlrpc.client.Fault as err:
    print(f"XML-RPC Fault: {err}")
except Exception as e:
    print(f"An error occurred: {e}")
