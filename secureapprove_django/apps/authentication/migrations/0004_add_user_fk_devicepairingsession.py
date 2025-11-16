from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0003_devicepairingsession_table"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
-- Ensure user_id column exists
ALTER TABLE "authentication_devicepairingsession"
    ADD COLUMN IF NOT EXISTS "user_id" bigint;

-- Ensure index on token exists
CREATE INDEX IF NOT EXISTS "authenticat_token_327f58_idx"
    ON "authentication_devicepairingsession" ("token");

-- Ensure composite index on (user_id, status) exists
CREATE INDEX IF NOT EXISTS "authenticat_user_id_4147a8_idx"
    ON "authentication_devicepairingsession" ("user_id", "status");

-- Ensure foreign key constraint exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'authentication_devicepairingsession'::regclass
          AND conname = 'authentication_devicepairingsession_user_id_fk'
    ) THEN
        ALTER TABLE "authentication_devicepairingsession"
            ADD CONSTRAINT "authentication_devicepairingsession_user_id_fk"
            FOREIGN KEY ("user_id")
            REFERENCES "authentication_user"("id")
            DEFERRABLE INITIALLY DEFERRED;
    END IF;
END$$;
""",
            reverse_sql="""
-- Drop foreign key and indices and column if they exist
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'authentication_devicepairingsession'::regclass
          AND conname = 'authentication_devicepairingsession_user_id_fk'
    ) THEN
        ALTER TABLE "authentication_devicepairingsession"
            DROP CONSTRAINT "authentication_devicepairingsession_user_id_fk";
    END IF;
END$$;

DROP INDEX IF EXISTS "authenticat_user_id_4147a8_idx";
DROP INDEX IF EXISTS "authenticat_token_327f58_idx";

ALTER TABLE "authentication_devicepairingsession"
    DROP COLUMN IF EXISTS "user_id";
""",
        ),
    ]

