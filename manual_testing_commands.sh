API_KEY = 

curl -i -X POST http://20.203.243.165/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@e.mail"}'

curl -X PUT http://20.203.243.165/api/users/USER_UUID/ \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: APIKEYHERE" \
  -d '{"email": "newemail@example.com"}'

curl -X DELETE http://20.203.243.165/api/users/USER_UUID/ \
  -H "X-Api-Key: APIKEYHERE"

curl http://20.203.243.165/api/products/

curl http://20.203.243.165/api/products/PRODUCT_HRUID/

curl -X POST http://20.203.243.165/api/products/ \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: APIKEYHERE" \
  -d '{
    "name": "Car 9000",
    "url": "https://example.com/product",
    "active": true
  }'

  curl -X POST http://20.203.243.165/api/products/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Car 9000",
    "url": "https://example.com/product",
    "active": true
  }'

curl -X PUT http://20.203.243.165/api/products/PRODUCT_HRUID/ \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: APIKEYHERE" \
  -d '{
    "name": "Updated Product Name",
    "url": "https://example.com/product-updated"
  }'

curl -X DELETE http://20.203.243.165/api/products/car-9000-1/ \
  -H "X-Api-Key: APIKEYHERE"

curl http://20.203.243.165/api/products/PRODUCT_HRUID/prices/

curl -X POST http://20.203.243.165/api/products/PRODUCT_HRUID/prices/ \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: APIKEYHERE" \
  -d '{
    "value": 99.99,
    "timestamp": "2026-01-15T12:00:00"
  }'

curl -X DELETE http://20.203.243.165/api/products/PRODUCT_HRUID/prices/PRICE_ID/ \
  -H "X-Api-Key: APIKEYHERE"