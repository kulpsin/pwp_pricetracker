API_KEY = 

curl -i -X POST http://127.0.0.1:5000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"email": "miro@e.mail"}'

curl -X PUT http://127.0.0.1:5000/api/users/USER_UUID/ \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: L7B30VROoni2w15LrG_OGuW0VjzaCUtn3XP_82BHiwQ" \
  -d '{"email": "newemail@example.com"}'

curl -X DELETE http://127.0.0.1:5000/api/users/USER_UUID/ \
  -H "X-Api-Key: L7B30VROoni2w15LrG_OGuW0VjzaCUtn3XP_82BHiwQ"

curl http://127.0.0.1:5000/api/products/

curl http://127.0.0.1:5000/api/products/PRODUCT_HRUID/

curl -X POST http://127.0.0.1:5000/api/products/ \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: L7B30VROoni2w15LrG_OGuW0VjzaCUtn3XP_82BHiwQ" \
  -d '{
    "name": "Car 9000",
    "url": "https://example.com/product",
    "active": true
  }'

  curl -X POST http://127.0.0.1:5000/api/products/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Car 9000",
    "url": "https://example.com/product",
    "active": true
  }'

curl -X PUT http://127.0.0.1:5000/api/products/PRODUCT_HRUID/ \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: L7B30VROoni2w15LrG_OGuW0VjzaCUtn3XP_82BHiwQ" \
  -d '{
    "name": "Updated Product Name",
    "url": "https://example.com/product-updated"
  }'

curl -X DELETE http://127.0.0.1:5000/api/products/car-9000-1/ \
  -H "X-Api-Key: L7B30VROoni2w15LrG_OGuW0VjzaCUtn3XP_82BHiwQ"

curl http://127.0.0.1:5000/api/products/PRODUCT_HRUID/prices/

curl -X POST http://127.0.0.1:5000/api/products/PRODUCT_HRUID/prices/ \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: L7B30VROoni2w15LrG_OGuW0VjzaCUtn3XP_82BHiwQ" \
  -d '{
    "value": 99.99,
    "timestamp": "2026-01-15T12:00:00"
  }'

curl -X DELETE http://127.0.0.1:5000/api/products/PRODUCT_HRUID/prices/PRICE_ID/ \
  -H "X-Api-Key: L7B30VROoni2w15LrG_OGuW0VjzaCUtn3XP_82BHiwQ"