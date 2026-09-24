#!/bin/bash

# Configuration settings
API_URL="http://127.0.0.1:5000/api/voucher/activate"
ROUTER_IP="192.168.88.1"
ROUTER_USER="admin"

echo "========================================="
echo "   WiFi Hotspot Gateway Authorization    "
echo "========================================="
echo -n "Please enter your access voucher code: "
read -r USER_CODE

# Validate token input field isn't empty
if [ -z "$USER_CODE" ]; then
    echo "Error: Voucher code cannot be blank."
    exit 1
fi

echo "Verifying voucher code sequence with backend billing infrastructure..."

# Fire an asynchronous JSON request directly into your billing.py Flask service
RESPONSE=$(curl -s -X POST "$API_URL" \
     -H "Content-Type: application/json" \
     -d "{\"code\": \"$USER_CODE\"}")

# Parse status values straight out of the JSON string
STATUS=$(echo "$RESPONSE" | grep -o '"status":"[^"]*' | grep -o '[^"]*$')
SPEED=$(echo "$RESPONSE" | grep -o '"speed_limit":"[^"]*' | grep -o '[^"]*$')

if [ "$STATUS" = "Authorized" ]; then
    echo "-----------------------------------------"
    echo "SUCCESS: Access Authorized!"
    echo "Assigned Speed Bandwidth Profile: $SPEED"
    echo "-----------------------------------------"
    
    # Push explicit authorization configurations back into your router interface hardware
    # Example command structure for MikroTik CLI API automation engines:
    echo "Executing hardware commands: SSH -> /ip hotspot active login user=$USER_CODE"
    # ssh "$ROUTER_USER@$ROUTER_IP" "/ip hotspot user add name=$USER_CODE profile=$SPEED"
    
    echo "Your terminal channel is now streaming. Welcome online!"
else
    # Output error rejection notices (Expired, Invalid, or Overused)
    ERR_MSG=$(echo "$RESPONSE" | grep -o '"message":"[^"]*' | grep -o '[^"]*$')
    echo "-----------------------------------------"
    echo "REJECTED: Authentication Failed."
    echo "Reason: $ERR_MSG"
    echo "-----------------------------------------"
    exit 1
fi