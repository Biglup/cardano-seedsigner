import pytest
from base import BaseTest
from seedsigner.models.settings import InvalidSettingsQRData, Settings
from seedsigner.models.settings_definition import SettingsConstants



class TestSettings(BaseTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.settings = Settings.get_instance()


    def test_reset_settings(self):
        """ BaseTest.reset_settings() should wipe out any previous Settings changes """
        settings = Settings.get_instance()
        settings.set_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS, SettingsConstants.OPTION__ENABLED)
        assert settings.get_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS) == SettingsConstants.OPTION__ENABLED

        BaseTest.reset_settings()
        settings = Settings.get_instance()
        assert settings.get_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS) == SettingsConstants.OPTION__DISABLED


    def test_parse_settingsqr_data(self):
        """
        SettingsQR parser should successfully parse a valid settingsqr input string and
        return the resulting config_name and formatted settings_update_dict.
        Removed Bitcoin-specific settings (coords, denom, network, sigs, scripts, partners)
        are ignored by the parser.
        """
        settings_name = "Test SettingsQR"
        settingsqr_data = f"""settings::v1 name={ settings_name.replace(" ", "_") } persistent=D qr_density=M passphrase=E camera=180 compact_seedqr=E priv_warn=E dire_warn=E"""

        # First explicitly set settings that differ from the settingsqr_data
        self.settings.set_value(SettingsConstants.SETTING__COMPACT_SEEDQR, SettingsConstants.OPTION__DISABLED)
        self.settings.set_value(SettingsConstants.SETTING__DIRE_WARNINGS, SettingsConstants.OPTION__DISABLED)

        # Now parse the settingsqr_data
        config_name, settings_update_dict = Settings.parse_settingsqr(settingsqr_data)
        assert config_name == settings_name
        self.settings.update(new_settings=settings_update_dict)

        # Now verify that the settings were updated correctly
        assert self.settings.get_value(SettingsConstants.SETTING__COMPACT_SEEDQR) == SettingsConstants.OPTION__ENABLED
        assert self.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS) == SettingsConstants.OPTION__ENABLED
    

    def test_settingsqr_version(self):
        """ SettingsQR parser should accept SettingsQR v1 and reject any others """
        settingsqr_data = "settings::v1 name=Foo"
        config_name, settings_update_dict = Settings.parse_settingsqr(settingsqr_data)

        # Accepts update with no Exceptions
        self.settings.update(new_settings=settings_update_dict)

        settingsqr_data = "settings::v2 name=Foo"
        with pytest.raises(InvalidSettingsQRData) as e:
            Settings.parse_settingsqr(settingsqr_data)
        assert "Unsupported SettingsQR version" in str(e.value)
    
        # Should also fail if version omitted
        settingsqr_data = "settings name=Foo"
        with pytest.raises(InvalidSettingsQRData) as e:
            Settings.parse_settingsqr(settingsqr_data)

        # And if "settings" is omitted entirely
        settingsqr_data = "name=Foo"
        with pytest.raises(InvalidSettingsQRData) as e:
            Settings.parse_settingsqr(settingsqr_data)


    def test_settingsqr_ignores_unrecognized_setting(self):
        """ SettingsQR parser should ignore unrecognized settings """
        settingsqr_data = "settings::v1 name=Foo favorite_food=bacon compact_seedqr=D"
        config_name, settings_update_dict = Settings.parse_settingsqr(settingsqr_data)

        assert "favorite_food" not in settings_update_dict
        assert "compact_seedqr" in settings_update_dict

        # Accepts update with no Exceptions
        self.settings.update(new_settings=settings_update_dict)


    def test_settingsqr_fails_unrecognized_option(self):
        """ SettingsQR parser should fail if a settings has an unrecognized option """
        settingsqr_data = "settings::v1 name=Foo compact_seedqr=Yep"
        with pytest.raises(InvalidSettingsQRData) as e:
            Settings.parse_settingsqr(settingsqr_data)
        assert "compact_seedqr" in str(e.value)


    def test_settingsqr_parses_line_break_separators(self):
        """ SettingsQR parser should read line breaks as acceptable separators """
        settingsqr_data = "settings::v1\nname=Foo\nqr_density=M\ncompact_seedqr=E\npassphrase=E\n"
        config_name, settings_update_dict = Settings.parse_settingsqr(settingsqr_data)

        assert len(settings_update_dict.keys()) == 3

        # Accepts update with no Exceptions
        self.settings.update(new_settings=settings_update_dict)
