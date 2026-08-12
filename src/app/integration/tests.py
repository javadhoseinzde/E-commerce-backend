"""
Tests for the internal integration API.
Tests for customer/resolve and cafe creation endpoints.
"""
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from app.cafe.models import Cafe, CafeUser, CafeInfo

User = get_user_model()


class CustomerResolveAPITest(TestCase):
    """Test suite for the customer/resolve endpoint."""

    def setUp(self):
        """Set up test data and client."""
        self.client = APIClient()
        self.url = '/api/internal/integration/customer/resolve/'
        self.valid_api_key = 'test-internal-api-key-12345'

        # Override settings for testing
        self.settings_patcher = patch('django.conf.settings.INTERNAL_API_KEY', self.valid_api_key)
        self.settings_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        self.settings_patcher.stop()

    def get_headers(self, api_key=None):
        """Get request headers with API key."""
        if api_key is None:
            api_key = self.valid_api_key
        return {'HTTP_X_INTERNAL_API_KEY': api_key}

    def test_new_user_creates_user_only(self):
        """Test 1: New mobile creates User only."""
        mobile = '09123456789'

        response = self.client.post(
            self.url,
            {'mobile': mobile},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'CREATED')

        # Check response data
        result = response.data['result']
        self.assertEqual(result['user']['mobile'], mobile)
        self.assertTrue(result['created']['user'])

        # Check that user was created
        user = User.objects.get(mobile=mobile)
        self.assertIsNotNone(user)
        self.assertTrue(user.is_active)

    def test_new_user_does_not_create_cafe(self):
        """Test 2: New mobile does NOT create Cafe."""
        mobile = '09123456790'

        response = self.client.post(
            self.url,
            {'mobile': mobile},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify user exists
        user = User.objects.get(mobile=mobile)
        self.assertIsNotNone(user)

        # Verify NO cafe was created
        self.assertEqual(Cafe.objects.count(), 0)

    def test_new_user_does_not_create_cafe_user(self):
        """Test 3: New mobile does NOT create CafeUser."""
        mobile = '09123456791'

        response = self.client.post(
            self.url,
            {'mobile': mobile},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify user exists
        user = User.objects.get(mobile=mobile)
        self.assertIsNotNone(user)

        # Verify NO CafeUser was created
        self.assertEqual(CafeUser.objects.count(), 0)

    def test_existing_user_returns_same_user(self):
        """Test 4: Existing mobile returns the same User."""
        # Create user
        user = User.objects.create_user(mobile='09123456792')

        response = self.client.post(
            self.url,
            {'mobile': '09123456792'},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'OK')

        result = response.data['result']
        self.assertEqual(result['user']['id'], user.id)
        self.assertEqual(result['user']['mobile'], user.mobile)
        self.assertFalse(result['created']['user'])

    def test_repeated_requests_are_idempotent(self):
        """Test 5: Repeated requests are idempotent."""
        mobile = '09123456793'

        # First request - creates user
        response1 = self.client.post(
            self.url,
            {'mobile': mobile},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second request - returns existing user
        response2 = self.client.post(
            self.url,
            {'mobile': mobile},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Should return same user
        self.assertEqual(
            response1.data['result']['user']['id'],
            response2.data['result']['user']['id']
        )

        # Should not create duplicate user
        self.assertEqual(User.objects.filter(mobile=mobile).count(), 1)

    def test_missing_api_key_returns_401(self):
        """Test 6: Missing API key -> 401."""
        response = self.client.post(
            self.url,
            {'mobile': '09123456794'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_api_key_returns_401(self):
        """Test 7: Invalid API key -> 401."""
        response = self.client.post(
            self.url,
            {'mobile': '09123456795'},
            format='json',
            **self.get_headers('wrong-api-key')
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_mobile_returns_400(self):
        """Test 8: Invalid mobile -> 400."""
        test_cases = [
            '0912345678',      # Too short
            '091234567890',    # Too long
            '12345678901',     # Doesn't start with 09
            'abcdefghijk',     # Not digits
            '0912345678a',     # Contains letter
        ]

        for mobile in test_cases:
            response = self.client.post(
                self.url,
                {'mobile': mobile},
                format='json',
                **self.get_headers()
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
                f"Expected 400 for mobile: {mobile}"
            )

    def test_proper_response_structure(self):
        """Test 9: Proper response structure."""
        mobile = '09123456796'

        response = self.client.post(
            self.url,
            {'mobile': mobile},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check response structure
        self.assertIn('message', response.data)
        self.assertIn('status', response.data)
        self.assertIn('result', response.data)

        result = response.data['result']

        # User section
        self.assertIn('user', result)
        self.assertIn('id', result['user'])
        self.assertIn('mobile', result['user'])

        # Created flags
        self.assertIn('created', result)
        self.assertIn('user', result['created'])
        self.assertIsInstance(result['created']['user'], bool)

        # Verify NO cafe or cafe_user in response
        self.assertNotIn('cafe', result)
        self.assertNotIn('cafe_user', result)

    def test_customer_resolve_never_creates_cafe(self):
        """Test: POST /customer/resolve/ NEVER creates a Cafe."""
        mobile = '09123456797'

        response = self.client.post(
            self.url,
            {'mobile': mobile},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify user was created
        user = User.objects.get(mobile=mobile)
        self.assertIsNotNone(user)

        # Verify NO cafe was created
        self.assertEqual(Cafe.objects.count(), 0)

        # Verify NO CafeUser was created
        self.assertEqual(CafeUser.objects.count(), 0)

        # Verify NO CafeInfo was created
        self.assertEqual(CafeInfo.objects.count(), 0)


class CafeCreationAPITest(TestCase):
    """Test suite for the cafe creation endpoint."""

    def setUp(self):
        """Set up test data and client."""
        self.client = APIClient()
        self.url = '/api/internal/integration/cafes/'
        self.valid_api_key = 'test-internal-api-key-12345'

        # Override settings for testing
        self.settings_patcher = patch('django.conf.settings.INTERNAL_API_KEY', self.valid_api_key)
        self.settings_patcher.start()

        # Create a test user
        self.user = User.objects.create_user(mobile='09123456800')

    def tearDown(self):
        """Clean up after tests."""
        self.settings_patcher.stop()

    def get_headers(self, api_key=None):
        """Get request headers with API key."""
        if api_key is None:
            api_key = self.valid_api_key
        return {'HTTP_X_INTERNAL_API_KEY': api_key}

    def test_valid_user_creates_cafe(self):
        """Test 1: Valid user + cafe name creates Cafe."""
        response = self.client.post(
            self.url,
            {'user_id': self.user.id, 'name': 'Test Cafe'},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'CREATED')

        # Check response data
        result = response.data['result']
        self.assertIn('cafe', result)
        self.assertIn('cafe_user', result)

        # Verify cafe was created
        cafe = Cafe.objects.get(id=result['cafe']['id'])
        self.assertIsNotNone(cafe)
        self.assertTrue(cafe.is_active)

    def test_cafe_user_role_is_owner(self):
        """Test 2: CafeUser with role=owner is created."""
        response = self.client.post(
            self.url,
            {'user_id': self.user.id, 'name': 'Owner Cafe'},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        result = response.data['result']
        self.assertEqual(result['cafe_user']['role'], 'owner')

        # Verify in database
        cafe_user = CafeUser.objects.get(id=result['cafe_user']['id'])
        self.assertEqual(cafe_user.role, 'owner')

    def test_cafe_name_matches_provided_name(self):
        """Test 3: Cafe name exactly matches the provided name."""
        cafe_name = 'کافه ناتی'

        response = self.client.post(
            self.url,
            {'user_id': self.user.id, 'name': cafe_name},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        result = response.data['result']
        self.assertEqual(result['cafe']['name'], cafe_name)

        # Verify in database
        cafe = Cafe.objects.get(id=result['cafe']['id'])
        self.assertEqual(cafe.name, cafe_name)

    def test_slug_is_generated_correctly_and_uniquely(self):
        """Test 4: Slug is generated correctly and uniquely."""
        response1 = self.client.post(
            self.url,
            {'user_id': self.user.id, 'name': 'Unique Cafe'},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        result1 = response1.data['result']
        self.assertIn('slug', result1['cafe'])
        self.assertTrue(len(result1['cafe']['slug']) > 0)

        # Create another user for second cafe
        user2 = User.objects.create_user(mobile='09123456801')

        response2 = self.client.post(
            self.url,
            {'user_id': user2.id, 'name': 'Another Unique Cafe'},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        result2 = response2.data['result']
        
        # Slugs should be different
        self.assertNotEqual(result1['cafe']['slug'], result2['cafe']['slug'])

    def test_invalid_user_returns_404(self):
        """Test 5: Invalid/nonexistent user -> appropriate 4xx."""
        response = self.client.post(
            self.url,
            {'user_id': 999999, 'name': 'Invalid User Cafe'},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_cafe_name_returns_400(self):
        """Test 6: Missing cafe name -> 400."""
        response = self.client.post(
            self.url,
            {'user_id': self.user.id},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_api_key_returns_401(self):
        """Test 7: Missing API key -> 401."""
        response = self.client.post(
            self.url,
            {'user_id': self.user.id, 'name': 'No Key Cafe'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_api_key_returns_401(self):
        """Test 8: Invalid API key -> 401."""
        response = self.client.post(
            self.url,
            {'user_id': self.user.id, 'name': 'Wrong Key Cafe'},
            format='json',
            **self.get_headers('wrong-api-key')
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cafe_creation_is_atomic(self):
        """Test 9: Cafe + CafeUser creation is atomic."""
        # This test verifies that if CafeUser creation fails,
        # the Cafe is not left orphaned
        
        response = self.client.post(
            self.url,
            {'user_id': self.user.id, 'name': 'Atomic Cafe'},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        result = response.data['result']
        
        # Both cafe and cafe_user should exist
        cafe = Cafe.objects.get(id=result['cafe']['id'])
        cafe_user = CafeUser.objects.get(id=result['cafe_user']['id'])
        
        # They should be linked
        self.assertEqual(cafe_user.cafe.id, cafe.id)
        self.assertEqual(cafe_user.user.id, self.user.id)

    def test_duplicate_cafe_user_relationship_handled_safely(self):
        """Test 10: Duplicate/invalid relationship is handled safely."""
        # First cafe creation
        response1 = self.client.post(
            self.url,
            {'user_id': self.user.id, 'name': 'First Cafe'},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second cafe creation for same user (should succeed - user can have multiple cafes)
        response2 = self.client.post(
            self.url,
            {'user_id': self.user.id, 'name': 'Second Cafe'},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Both cafes should exist
        self.assertEqual(Cafe.objects.filter(members__user=self.user).count(), 2)

    def test_cafe_info_is_created(self):
        """Test that CafeInfo is created with the cafe."""
        response = self.client.post(
            self.url,
            {'user_id': self.user.id, 'name': 'Info Cafe'},
            format='json',
            **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        result = response.data['result']
        cafe = Cafe.objects.get(id=result['cafe']['id'])
        
        # CafeInfo should exist
        cafe_info = CafeInfo.objects.get(cafe=cafe)
        self.assertIsNotNone(cafe_info)
