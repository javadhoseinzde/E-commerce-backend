"""
Services for the internal integration API.
Contains business logic for customer resolution and cafe creation.
"""
import uuid
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.utils.text import slugify

from app.users.models import MyUser
from app.cafe.models import Cafe, CafeUser, CafeInfo


class CustomerResolutionService:
    """
    Service for resolving or creating users based on mobile number.
    Only handles user creation - does NOT create Cafe or CafeUser.
    """

    @staticmethod
    def resolve_or_create_user(mobile: str) -> tuple[MyUser, bool]:
        """
        Resolve or create a user based on mobile number.
        
        Args:
            mobile: The mobile number to resolve
            
        Returns:
            Tuple of (user, created) where created is True if a new user was created
            
        Raises:
            ValueError: If mobile format is invalid
        """
        user_created = False
        try:
            with transaction.atomic():
                user, user_created = MyUser.objects.get_or_create(
                    mobile=mobile,
                    defaults={
                        'is_active': True,
                    }
                )
        except IntegrityError:
            # Race condition: another thread created the user between our check and create
            user = MyUser.objects.get(mobile=mobile)
            user_created = False

        return user, user_created


class CafeCreationService:
    """
    Service for creating cafes with proper validation and atomic operations.
    """

    @staticmethod
    def generate_unique_slug(name: str, exclude_id: int = None) -> str:
        """
        Generate a unique slug for a cafe.
        Handles concurrent requests safely.
        
        Args:
            name: The cafe name to generate slug from
            exclude_id: Optional ID to exclude from uniqueness check
            
        Returns:
            Unique slug string
        """
        base_slug = slugify(name)
        if not base_slug:
            base_slug = 'cafe'
        
        slug = base_slug
        counter = 1
        
        while counter <= 100:
            query = Q(slug=slug)
            if exclude_id:
                query &= ~Q(id=exclude_id)
            
            if not Cafe.objects.filter(query).exists():
                return slug
            
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Final fallback with UUID
        return f"{base_slug}-{uuid.uuid4().hex[:8]}"

    @staticmethod
    def create_cafe(user_id: int, cafe_name: str) -> tuple[Cafe, CafeUser]:
        """
        Create a cafe and CafeUser with owner role atomically.
        
        Args:
            user_id: The user ID to associate with the cafe
            cafe_name: The name of the cafe to create
            
        Returns:
            Tuple of (cafe, cafe_user) objects
            
        Raises:
            MyUser.DoesNotExist: If user does not exist
            ValueError: If cafe name is invalid or already exists for user
        """
        # Validate that the user exists
        try:
            user = MyUser.objects.get(id=user_id)
        except MyUser.DoesNotExist:
            raise MyUser.DoesNotExist(f"User with id {user_id} does not exist")

        # Validate cafe name
        if not cafe_name or not cafe_name.strip():
            raise ValueError("Cafe name cannot be empty")
        
        cafe_name = cafe_name.strip()

        # Create cafe and cafe user atomically
        # Handle concurrent creation with IntegrityError retry
        max_retries = 5
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    cafe_slug = CafeCreationService.generate_unique_slug(cafe_name)
                    
                    cafe = Cafe.objects.create(
                        name=cafe_name,
                        slug=cafe_slug,
                        is_active=True
                    )
                    
                    cafe_user = CafeUser.objects.create(
                        cafe=cafe,
                        user=user,
                        role="owner"
                    )
                    
                    # Create cafe info
                    CafeInfo.objects.create(cafe=cafe)
                    
                return cafe, cafe_user
            except IntegrityError:
                if attempt < max_retries - 1:
                    # Slug collision or other integrity error - retry with new slug
                    continue
                else:
                    # Final attempt failed
                    raise

    @staticmethod
    def get_user_cafes(user_id: int) -> list[dict]:
        """
        Get all cafes for a user.
        
        Args:
            user_id: The user ID to get cafes for
            
        Returns:
            List of cafe dictionaries
        """
        cafe_users = CafeUser.objects.filter(user_id=user_id).select_related('cafe')
        return [
            {
                'id': cu.cafe.id,
                'name': cu.cafe.name,
                'slug': cu.cafe.slug,
                'is_active': cu.cafe.is_active
            }
            for cu in cafe_users
        ]
