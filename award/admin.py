from django.contrib import admin

from award.models import Lecturer, Nomination, Verification


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'faculty')
    list_filter = ('faculty',)


@admin.register(Nomination)
class NominationAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'lecturer', 'sub_date', 'is_verified')
    list_filter = ('is_verified', )


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = ('nomination', 'created', 'is_expired')
    list_filter = ('nomination',)
