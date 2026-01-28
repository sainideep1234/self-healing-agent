"""
Test Script for Self-Healing API Gateway

This script demonstrates the healing capabilities by:
1. Making requests through the gateway in STABLE mode (no healing needed)
2. Switching to DRIFTED mode (schema changes)
3. Observing the LLM-powered healing in action
4. Verifying cached mappings work for subsequent requests
"""
import asyncio
import httpx
import json
from datetime import datetime


# Configuration
GATEWAY_URL = "http://localhost:8000"
MOCK_API_URL = "http://localhost:8001"


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"🔹 {text}")
    print("=" * 60)


def print_json(data: dict):
    """Pretty print JSON."""
    print(json.dumps(data, indent=2, default=str))


async def check_health():
    """Check if all services are healthy."""
    print_header("Checking Service Health")
    
    async with httpx.AsyncClient() as client:
        # Check gateway
        try:
            r = await client.get(f"{GATEWAY_URL}/admin/health")
            print(f"✅ Gateway: {r.json()['status']}")
        except Exception as e:
            print(f"❌ Gateway: {e}")
            return False
        
        # Check mock API
        try:
            r = await client.get(f"{MOCK_API_URL}/health")
            print(f"✅ Mock API: {r.json()['status']}")
        except Exception as e:
            print(f"❌ Mock API: {e}")
            return False
    
    return True


async def set_mock_mode(mode: str):
    """Set the mock API schema mode."""
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{MOCK_API_URL}/mode?mode={mode}")
        print(f"📊 Mock API mode set to: {r.json()['mode']}")


async def clear_cache():
    """Clear all cached mappings."""
    async with httpx.AsyncClient() as client:
        r = await client.delete(f"{GATEWAY_URL}/admin/mappings")
        print(f"🗑️  Cleared {r.json()['cleared']} cached mappings")


async def make_request(endpoint: str, description: str) -> dict:
    """Make a request through the gateway."""
    print(f"\n📤 Request: GET {endpoint}")
    print(f"   ({description})")
    
    async with httpx.AsyncClient() as client:
        start = datetime.now()
        r = await client.get(f"{GATEWAY_URL}{endpoint}")
        duration = (datetime.now() - start).total_seconds() * 1000
        
        # Check for healing headers
        healed = r.headers.get("X-Schema-Healed", "false") == "true"
        cache_status = r.headers.get("X-Healing-Cache", "n/a")
        
        print(f"📥 Response ({r.status_code}) - {duration:.0f}ms")
        print(f"   Healed: {healed}, Cache: {cache_status}")
        
        data = r.json()
        
        # Show truncated response
        response_str = json.dumps(data, indent=2, default=str)
        if len(response_str) > 500:
            print(f"   Body: {response_str[:500]}...")
        else:
            print(f"   Body: {response_str}")
        
        return data


async def test_stable_mode():
    """Test with stable (expected) schema."""
    print_header("Test 1: STABLE Mode (No Healing Needed)")
    
    await set_mock_mode("stable")
    await clear_cache()
    
    # Request user
    await make_request("/api/users/1", "Expected schema - should pass validation")
    
    # Request products
    await make_request("/api/products", "Expected schema - should pass validation")
    
    print("\n✅ Stable mode test completed. No healing was needed.")


async def test_drifted_mode():
    """Test with drifted (changed) schema."""
    print_header("Test 2: DRIFTED Mode (Schema Changed - Healing Required)")
    
    await set_mock_mode("drifted")
    await clear_cache()
    
    print("\n⚠️  The mock API is now returning DIFFERENT field names:")
    print("   - user_id → uid")
    print("   - name → full_name")
    print("   - email → email_address")
    print("   - created_at → registered_date")
    print("\n🤖 The LLM agent will now analyze and heal the schema mismatch...\n")
    
    # This should trigger healing!
    await make_request("/api/users/1", "Drifted schema - LLM will generate mapping")
    
    print("\n🔄 Making same request again (should use cached mapping)...\n")
    
    # This should use cached mapping
    await make_request("/api/users/1", "Using cached mapping - instant!")


async def test_product_drift():
    """Test product schema drift."""
    print_header("Test 3: Product Schema Drift")
    
    await set_mock_mode("drifted")
    
    print("\n⚠️  Product schema has changed:")
    print("   - product_id → id")
    print("   - title → product_name")
    print("   - price → cost")
    print("   - in_stock → available")
    print()
    
    # Trigger healing for products
    await make_request("/api/products/101", "Product schema drift - will heal")


async def show_stats():
    """Show healing statistics."""
    print_header("Healing Statistics")
    
    async with httpx.AsyncClient() as client:
        # Get stats
        r = await client.get(f"{GATEWAY_URL}/admin/stats?hours=1")
        print_json(r.json())
        
        # Get cached mappings
        r = await client.get(f"{GATEWAY_URL}/admin/mappings")
        mappings = r.json()
        print(f"\n📦 Cached Mappings: {mappings['total']}")
        
        for mapping in mappings.get("mappings", []):
            print(f"   - {mapping['endpoint']} (v{mapping['version']})")
            for fm in mapping.get("field_mappings", []):
                print(f"     {fm['source_field']} → {fm['target_field']} ({fm['confidence']*100:.0f}%)")


async def main():
    """Run all tests."""
    print("\n" + "🔧" * 30)
    print("   SELF-HEALING API GATEWAY - TEST SUITE")
    print("🔧" * 30)
    
    # Check health
    if not await check_health():
        print("\n❌ Services not healthy. Please start:")
        print("   1. docker-compose up -d (Redis & MongoDB)")
        print("   2. ./run_mock_api.sh")
        print("   3. ./run_gateway.sh")
        return
    
    # Run tests
    await test_stable_mode()
    
    print("\n" + "⏳" * 20)
    print("   Waiting 2 seconds before drift test...")
    print("⏳" * 20)
    await asyncio.sleep(2)
    
    await test_drifted_mode()
    await test_product_drift()
    
    await show_stats()
    
    print_header("Test Suite Complete! 🎉")
    print("""
Summary:
--------
1. In STABLE mode, the proxy simply forwards requests (no healing).
2. In DRIFTED mode, the proxy detects schema mismatches.
3. The LLM agent analyzes the mismatch and generates field mappings.
4. Mappings are cached in Redis for instant subsequent requests.
5. All healing events are logged to MongoDB for analytics.

This demonstrates "Self-Healing Workflows" - a core capability 
for maintaining reliable API integrations in production.
    """)


if __name__ == "__main__":
    asyncio.run(main())
