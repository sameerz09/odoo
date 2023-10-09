import xmlrpc.client


url = 'http://localhost:9069'
db = 'TEST'
username='sameerz09@hotmail.com'
password='Test@111'
account_id = 11
target_date = '2023-10-08'


common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
print (common.version());
uid = common.authenticate(db, username, password, {})

print("UID", uid)

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
partners = models.execute_kw(db, uid, password, 'res.partner', 'search', [[['is_company', '=', True]]], {'offset': 2, 'limit': 3})
print('----->',partners)

balance = models.execute_kw(db, uid, password, 'account.account', 'getbalance', [account_id, target_date])

print ('test', balance)
