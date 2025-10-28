def filter_by_user_role(queryset, user):
    if hasattr(user, 'employee'):
        return queryset.filter(dormitory=user.employee.dormitory)
    elif hasattr(user, 'director'):
        dormitories = user.director.dormitories.all()
        return queryset.filter(dormitory__in=dormitories)
    elif user.is_superuser:
        return queryset
    else:
        return queryset.none()

def filter_by_user_role_payment(queryset, user):
    if hasattr(user, 'employee'):
        return queryset.filter(student__dormitory=user.employee.dormitory)
    elif hasattr(user, 'director'):
        dormitories = user.director.dormitories.all()
        return queryset.filter(student__dormitory__in=dormitories)
    return queryset