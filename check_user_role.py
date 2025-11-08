"""
Quick script to check and update user roles.
Run this with: python manage.py shell < check_user_role.py
Or run: python manage.py shell, then paste the code below.
"""

from accounts.models import User

# List all users and their roles
print("All users and their roles:")
for user in User.objects.all():
    print(f"  {user.username} ({user.email}): {user.role}")

# To update a specific user to instructor:
# user = User.objects.get(username='your_username')
# user.role = User.Role.INSTRUCTOR
# user.save()
# print(f"Updated {user.username} to instructor")

