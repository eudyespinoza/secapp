from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0002_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
CREATE TABLE IF NOT EXISTS "authentication_devicepairingsession" (
    "id" uuid NOT NULL PRIMARY KEY,
    "token" varchar(128) NOT NULL UNIQUE,
    "status" varchar(20) NOT NULL DEFAULT 'pending',
    "created_at" timestamp with time zone NOT NULL,
    "expires_at" timestamp with time zone NOT NULL,
    "paired_at" timestamp with time zone NULL,
    "paired_user_agent" text NOT NULL DEFAULT '',
    "paired_platform" varchar(255) NOT NULL DEFAULT ''
);
""",
            reverse_sql="""
DROP TABLE IF EXISTS "authentication_devicepairingsession";
""",
        ),
    ]

