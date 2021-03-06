# Generated by Django 3.2 on 2021-05-19 19:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('award', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='nomination',
            name='check_domain_whitelist',
        ),
        migrations.RemoveConstraint(
            model_name='nomination',
            name='unique_nomination',
        ),
        migrations.RenameField(
            model_name='nomination',
            old_name='verified',
            new_name='is_verified',
        ),
        migrations.AddField(
            model_name='nomination',
            name='is_student',
            field=models.BooleanField(default=True),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name='nomination',
            constraint=models.CheckConstraint(check=models.Q(sub_email__endswith='@ovgu.de'), name='check_domain_whitelist'),
        ),
        migrations.AddConstraint(
            model_name='nomination',
            constraint=models.UniqueConstraint(fields=('lecturer', 'sub_email'), name='unique_nomination'),
        ),
    ]
