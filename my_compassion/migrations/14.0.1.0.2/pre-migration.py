from openupgradelib import openupgrade

def migrate(cr, version):
    openupgrade.logged_query(
        cr,
        """
        ALTER TABLE compassion_project
        ADD COLUMN IF NOT EXISTS gps_latitude_obfuscated DECIMAL(10, 6),
        ADD COLUMN IF NOT EXISTS gps_longitude_obfuscated DECIMAL(10, 6)
        """
    )