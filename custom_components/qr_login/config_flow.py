"""Config and options flow for QR Login."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    ADD_MAPPING_SENTINEL,
    CONF_CHANNEL,
    CONF_DEFAULT_CHANNEL,
    CONF_ENABLED_CHANNELS,
    CONF_NOTIFICATION_COOLDOWN,
    CONF_NOTIFY_TARGET,
    CONF_RATE_LIMIT_GLOBAL,
    CONF_RATE_LIMIT_GLOBAL_WINDOW,
    CONF_RATE_LIMIT_IP,
    CONF_RATE_LIMIT_IP_WINDOW,
    CONF_RECAPTCHA_SECRET_KEY,
    CONF_RECAPTCHA_SITE_KEY,
    CONF_RECAPTCHA_THRESHOLD,
    CONF_SESSION_TIMEOUT,
    CONF_TARGET_USER,
    CONF_USER_MAPPINGS,
    DEFAULT_CHANNEL,
    DEFAULT_ENABLED_CHANNELS,
    DEFAULT_NOTIFICATION_COOLDOWN,
    DEFAULT_RATE_LIMIT_GLOBAL,
    DEFAULT_RATE_LIMIT_GLOBAL_WINDOW,
    DEFAULT_RATE_LIMIT_IP,
    DEFAULT_RATE_LIMIT_IP_WINDOW,
    DEFAULT_RECAPTCHA_THRESHOLD,
    DEFAULT_SESSION_TIMEOUT,
    DOMAIN,
    DONE_ACTION,
    VALID_CHANNELS,
)

RESERVED_USERNAMES = frozenset({ADD_MAPPING_SENTINEL, DONE_ACTION})

DELETE_FIELD = "delete"


class QRLoginConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="QR Login",
                data=user_input,
                options=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEFAULT_CHANNEL, default=DEFAULT_CHANNEL
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=VALID_CHANNELS,
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="channel",
                        )
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return QRLoginOptionsFlow(config_entry)


class QRLoginOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._options = dict(config_entry.options)
        self._mappings = dict(
            self._options.get(CONF_USER_MAPPINGS, {})
        )
        self._edit_username = None

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=["main", "mappings"],
        )

    _SECTION_KEYS = ("channels", "recaptcha", "rate_limiting", "notifications")

    # An optional text field that is cleared comes back as undefined, so it is
    # simply absent from user_input. These have to be forced back to empty or
    # the previous value would survive and the feature could not be turned off.
    _CLEARABLE = (CONF_RECAPTCHA_SITE_KEY, CONF_RECAPTCHA_SECRET_KEY)

    async def async_step_main(self, user_input=None):
        if user_input is not None:
            flat = self._flatten_sections(user_input)
            for key in self._CLEARABLE:
                flat[key] = (flat.get(key) or "").strip()
            schema_options = {**self._options, **flat}

            if not flat.get(CONF_ENABLED_CHANNELS):
                return self.async_show_form(
                    step_id="main",
                    data_schema=self._main_schema(schema_options),
                    errors={"channels.enabled_channels": "at_least_one"},
                )

            # Only one of the two keys makes login impossible: the page needs
            # the site key to mint a token the server then demands.
            if bool(flat[CONF_RECAPTCHA_SITE_KEY]) != bool(
                flat[CONF_RECAPTCHA_SECRET_KEY]
            ):
                return self.async_show_form(
                    step_id="main",
                    data_schema=self._main_schema(schema_options),
                    errors={"recaptcha.recaptcha_site_key": "recaptcha_incomplete"},
                )
            self._options.update(flat)
            self._options[CONF_USER_MAPPINGS] = self._mappings
            return self.async_create_entry(title="", data=self._options)

        return self.async_show_form(
            step_id="main",
            data_schema=self._main_schema(self._options),
            last_step=False,
        )

    @classmethod
    def _flatten_sections(cls, user_input):
        flat = {}
        for key, value in user_input.items():
            if key in cls._SECTION_KEYS and isinstance(value, dict):
                flat.update(value)
            else:
                flat[key] = value
        return flat

    def _main_schema(self, options):
        return vol.Schema(
            {
                vol.Required("channels"): section(
                    vol.Schema(
                        {
                            vol.Required(
                                CONF_ENABLED_CHANNELS,
                                default=options.get(
                                    CONF_ENABLED_CHANNELS, DEFAULT_ENABLED_CHANNELS
                                ),
                            ): SelectSelector(
                                SelectSelectorConfig(
                                    options=VALID_CHANNELS,
                                    multiple=True,
                                    mode=SelectSelectorMode.LIST,
                                    translation_key="channel",
                                )
                            ),
                            vol.Optional(
                                CONF_DEFAULT_CHANNEL,
                                default=options.get(
                                    CONF_DEFAULT_CHANNEL, DEFAULT_CHANNEL
                                ),
                            ): SelectSelector(
                                SelectSelectorConfig(
                                    options=VALID_CHANNELS,
                                    mode=SelectSelectorMode.DROPDOWN,
                                    translation_key="channel",
                                )
                            ),
                        }
                    ),
                    {"collapsed": False},
                ),
                vol.Required("recaptcha"): section(
                    vol.Schema(
                        {
                            vol.Optional(
                                CONF_RECAPTCHA_SITE_KEY,
                                description={
                                    "suggested_value": options.get(
                                        CONF_RECAPTCHA_SITE_KEY, ""
                                    )
                                },
                            ): TextSelector(
                                TextSelectorConfig(type=TextSelectorType.TEXT)
                            ),
                            vol.Optional(
                                CONF_RECAPTCHA_SECRET_KEY,
                                description={
                                    "suggested_value": options.get(
                                        CONF_RECAPTCHA_SECRET_KEY, ""
                                    )
                                },
                            ): TextSelector(
                                TextSelectorConfig(type=TextSelectorType.PASSWORD)
                            ),
                            vol.Optional(
                                CONF_RECAPTCHA_THRESHOLD,
                                default=options.get(
                                    CONF_RECAPTCHA_THRESHOLD,
                                    DEFAULT_RECAPTCHA_THRESHOLD,
                                ),
                            ): NumberSelector(
                                NumberSelectorConfig(
                                    min=0.0,
                                    max=1.0,
                                    step=0.05,
                                    mode=NumberSelectorMode.SLIDER,
                                )
                            ),
                        }
                    ),
                    {"collapsed": True},
                ),
                vol.Required("rate_limiting"): section(
                    vol.Schema(
                        {
                            vol.Optional(
                                CONF_RATE_LIMIT_IP,
                                default=options.get(
                                    CONF_RATE_LIMIT_IP, DEFAULT_RATE_LIMIT_IP
                                ),
                            ): NumberSelector(
                                NumberSelectorConfig(
                                    min=1, max=100, mode=NumberSelectorMode.BOX
                                )
                            ),
                            vol.Optional(
                                CONF_RATE_LIMIT_IP_WINDOW,
                                default=options.get(
                                    CONF_RATE_LIMIT_IP_WINDOW,
                                    DEFAULT_RATE_LIMIT_IP_WINDOW,
                                ),
                            ): NumberSelector(
                                NumberSelectorConfig(
                                    min=1, max=3600, mode=NumberSelectorMode.BOX
                                )
                            ),
                            vol.Optional(
                                CONF_RATE_LIMIT_GLOBAL,
                                default=options.get(
                                    CONF_RATE_LIMIT_GLOBAL, DEFAULT_RATE_LIMIT_GLOBAL
                                ),
                            ): NumberSelector(
                                NumberSelectorConfig(
                                    min=1, max=1000, mode=NumberSelectorMode.BOX
                                )
                            ),
                            vol.Optional(
                                CONF_RATE_LIMIT_GLOBAL_WINDOW,
                                default=options.get(
                                    CONF_RATE_LIMIT_GLOBAL_WINDOW,
                                    DEFAULT_RATE_LIMIT_GLOBAL_WINDOW,
                                ),
                            ): NumberSelector(
                                NumberSelectorConfig(
                                    min=1, max=3600, mode=NumberSelectorMode.BOX
                                )
                            ),
                        }
                    ),
                    {"collapsed": True},
                ),
                vol.Required("notifications"): section(
                    vol.Schema(
                        {
                            vol.Optional(
                                CONF_NOTIFICATION_COOLDOWN,
                                default=options.get(
                                    CONF_NOTIFICATION_COOLDOWN,
                                    DEFAULT_NOTIFICATION_COOLDOWN,
                                ),
                            ): NumberSelector(
                                NumberSelectorConfig(
                                    min=1, max=3600, mode=NumberSelectorMode.BOX
                                )
                            ),
                            vol.Optional(
                                CONF_SESSION_TIMEOUT,
                                default=options.get(
                                    CONF_SESSION_TIMEOUT, DEFAULT_SESSION_TIMEOUT
                                ),
                            ): NumberSelector(
                                NumberSelectorConfig(
                                    min=30, max=600, mode=NumberSelectorMode.BOX
                                )
                            ),
                        }
                    ),
                    {"collapsed": True},
                ),
            }
        )

    async def async_step_mappings(self, user_input=None):
        if user_input is not None:
            selected = user_input.get("mapping")
            if selected == ADD_MAPPING_SENTINEL:
                return await self.async_step_add_mapping()
            if selected == DONE_ACTION:
                self._options[CONF_USER_MAPPINGS] = self._mappings
                return self.async_create_entry(title="", data=self._options)
            if selected in self._mappings:
                self._edit_username = selected
                return await self.async_step_edit_mapping()
            return await self.async_step_mappings()

        mapping_options = await self._mapping_options()
        options = [
            {"value": DONE_ACTION, "label": "Termina e salva"},
            {"value": ADD_MAPPING_SENTINEL, "label": "＋ Aggiungi nuovo mapping"},
            *mapping_options,
        ]

        return self.async_show_form(
            step_id="mappings",
            data_schema=vol.Schema(
                {
                    vol.Required("mapping", default=DONE_ACTION): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            description_placeholders={"count": str(len(self._mappings))},
            last_step=False,
        )

    async def _mapping_options(self):
        label_map = {}
        for user in await self.hass.auth.async_get_users():
            if user.name:
                label_map[user.id] = user.name

        result = []
        for username, mapping in self._mappings.items():
            target = mapping.get(CONF_TARGET_USER, username)
            target_label = label_map.get(target, target)
            channel = mapping.get(CONF_CHANNEL)
            if channel not in VALID_CHANNELS:
                channel = DEFAULT_CHANNEL
            result.append(
                {
                    "value": username,
                    "label": f"{username} → {target_label} ({channel})",
                }
            )
        return result

    async def _user_options(self):
        users = await self.hass.auth.async_get_users()
        result = [
            {"value": user.id, "label": user.name or user.id}
            for user in users
            if user.name and user.is_active and not user.system_generated
        ]
        result.sort(key=lambda item: item["label"].casefold())
        return result

    async def async_step_add_mapping(self, user_input=None):
        user_options = await self._user_options()

        if user_input is not None:
            username = (user_input.get("username") or "").strip()
            if not username:
                return self.async_show_form(
                    step_id="add_mapping",
                    data_schema=self._get_mapping_schema(user_options),
                    errors={"username": "required"},
                )
            if username in RESERVED_USERNAMES:
                return self.async_show_form(
                    step_id="add_mapping",
                    data_schema=self._get_mapping_schema(user_options),
                    errors={"username": "reserved"},
                )
            if username in self._mappings:
                return self.async_show_form(
                    step_id="add_mapping",
                    data_schema=self._get_mapping_schema(user_options),
                    errors={"username": "already_exists"},
                )

            self._mappings[username] = self._new_mapping(user_input, username)
            return await self.async_step_mappings()

        return self.async_show_form(
            step_id="add_mapping",
            data_schema=self._get_mapping_schema(user_options),
            last_step=False,
        )

    async def async_step_edit_mapping(self, user_input=None):
        username = self._edit_username
        if username is None or username not in self._mappings:
            return await self.async_step_mappings()

        mapping = self._mappings[username]
        user_options = await self._user_options()

        if user_input is not None:
            new_username = (user_input.get("username") or "").strip()
            if not new_username:
                return self.async_show_form(
                    step_id="edit_mapping",
                    data_schema=self._get_mapping_schema(
                        user_options, mapping, username
                    ),
                    errors={"username": "required"},
                )
            if new_username in RESERVED_USERNAMES:
                return self.async_show_form(
                    step_id="edit_mapping",
                    data_schema=self._get_mapping_schema(
                        user_options, mapping, username
                    ),
                    errors={"username": "reserved"},
                )
            if new_username != username and new_username in self._mappings:
                return self.async_show_form(
                    step_id="edit_mapping",
                    data_schema=self._get_mapping_schema(
                        user_options, mapping, username
                    ),
                    errors={"username": "already_exists"},
                )

            del self._mappings[username]
            if not user_input.get(DELETE_FIELD):
                self._mappings[new_username] = self._new_mapping(
                    user_input, new_username
                )
            self._edit_username = None
            return await self.async_step_mappings()

        return self.async_show_form(
            step_id="edit_mapping",
            data_schema=self._get_mapping_schema(user_options, mapping, username),
            last_step=False,
        )

    @staticmethod
    def _new_mapping(user_input, username):
        return {
            CONF_TARGET_USER: user_input.get(CONF_TARGET_USER) or username,
            CONF_NOTIFY_TARGET: (user_input.get(CONF_NOTIFY_TARGET) or "").strip(),
            CONF_CHANNEL: user_input.get(CONF_CHANNEL) or DEFAULT_CHANNEL,
        }

    def _get_mapping_schema(self, user_options, mapping=None, current_username=None):
        default_username = current_username or ""
        default_target = mapping.get(CONF_TARGET_USER, "") if mapping else ""
        default_notify = mapping.get(CONF_NOTIFY_TARGET, "") if mapping else ""

        stored_channel = mapping.get(CONF_CHANNEL) if mapping else None
        default_channel = (
            stored_channel if stored_channel in VALID_CHANNELS else DEFAULT_CHANNEL
        )

        target_options = list(user_options)
        if not default_target and target_options:
            default_target = target_options[0]["value"]
        if default_target and not any(
            item["value"] == default_target for item in target_options
        ):
            target_options.append(
                {
                    "value": default_target,
                    "label": f"{default_target} (utente non trovato)",
                }
            )

        notify_field = EntitySelector(EntitySelectorConfig(domain="notify"))
        if default_notify:
            notify_key = vol.Optional(CONF_NOTIFY_TARGET, default=default_notify)
        else:
            notify_key = vol.Optional(CONF_NOTIFY_TARGET)

        schema = {
            vol.Required("username", default=default_username): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(CONF_TARGET_USER, default=default_target): SelectSelector(
                SelectSelectorConfig(
                    options=target_options,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            notify_key: notify_field,
            vol.Required(CONF_CHANNEL, default=default_channel): SelectSelector(
                SelectSelectorConfig(
                    options=VALID_CHANNELS,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="channel",
                )
            ),
        }

        if mapping is not None:
            schema[vol.Optional(DELETE_FIELD, default=False)] = BooleanSelector()

        return vol.Schema(schema)
