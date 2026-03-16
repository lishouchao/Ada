"""
Dialogs - Various dialogs for Ada
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib

from typing import Optional, Callable


class ConfirmationDialog(Adw.MessageDialog):
    """
    Confirmation dialog for destructive actions.

    Usage:
        dialog = ConfirmationDialog(
            parent=window,
            title="Confirm Delete",
            message="Are you sure you want to delete this file?",
            confirm_label="Delete",
            destructive=True
        )
        dialog.show()
    """

    def __init__(
        self,
        parent: Gtk.Window,
        title: str,
        message: str,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        destructive: bool = False,
        on_confirm: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None
    ):
        super().__init__(
            transient_for=parent,
            heading=title,
            body=message,
        )

        self._on_confirm = on_confirm
        self._on_cancel = on_cancel

        # Add responses
        self.add_response("cancel", cancel_label)
        self.add_response("confirm", confirm_label)

        # Set destructive appearance
        if destructive:
            self.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
        else:
            self.set_response_appearance("confirm", Adw.ResponseAppearance.SUGGESTED)

        # Set default
        self.set_default_response("cancel")
        self.set_close_response("cancel")

        # Connect response
        self.connect("response", self._on_response)

    def _on_response(self, dialog, response_id):
        """Handle dialog response"""
        if response_id == "confirm" and self._on_confirm:
            self._on_confirm()
        elif response_id == "cancel" and self._on_cancel:
            self._on_cancel()


class PermissionDialog(Adw.MessageDialog):
    """
    Permission request dialog.

    Shows when an action requires user permission.
    """

    def __init__(
        self,
        parent: Gtk.Window,
        permission_name: str,
        permission_description: str,
        reason: str = None,
        on_allow: Optional[Callable] = None,
        on_deny: Optional[Callable] = None,
        on_allow_always: Optional[Callable] = None
    ):
        body = f"{permission_description}"
        if reason:
            body += f"\n\nReason: {reason}"

        super().__init__(
            transient_for=parent,
            heading=f"Permission Required: {permission_name}",
            body=body,
        )

        self._on_allow = on_allow
        self._on_deny = on_deny
        self._on_allow_always = on_allow_always

        # Add responses
        self.add_response("deny", "Deny")
        self.add_response("allow", "Allow Once")
        self.add_response("allow_always", "Always Allow")

        self.set_response_appearance("allow", Adw.ResponseAppearance.SUGGESTED)
        self.set_default_response("allow")
        self.set_close_response("deny")

        self.connect("response", self._on_response)

    def _on_response(self, dialog, response_id):
        """Handle dialog response"""
        if response_id == "allow" and self._on_allow:
            self._on_allow()
        elif response_id == "allow_always" and self._on_allow_always:
            self._on_allow_always()
        elif response_id == "deny" and self._on_deny:
            self._on_deny()


class SkillInfoDialog(Adw.Window):
    """
    Dialog showing skill information.
    """

    def __init__(self, parent: Gtk.Window, skill_metadata: dict):
        super().__init__(
            transient_for=parent,
            title=skill_metadata.get("name", "Skill"),
            default_width=400,
            default_height=500,
        )

        # Build content
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header
        header = Adw.HeaderBar()
        box.append(header)

        # Content
        content = Adw.Clamp(
            maximum_size=400,
            margin_top=24,
            margin_bottom=24,
            margin_start=24,
            margin_end=24,
        )

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Name
        name_label = Gtk.Label(
            label=skill_metadata.get("name", "Unknown"),
            css_classes=["title-1"],
        )
        content_box.append(name_label)

        # Description
        desc_label = Gtk.Label(
            label=skill_metadata.get("description", ""),
            wrap=True,
            xalign=0,
        )
        content_box.append(desc_label)

        # Metadata
        meta_group = Adw.PreferencesGroup(title="Details")

        # Version
        version_row = Adw.ActionRow(
            title="Version",
            subtitle=skill_metadata.get("version", "0.0.0"),
        )
        meta_group.add(version_row)

        # Category
        category_row = Adw.ActionRow(
            title="Category",
            subtitle=skill_metadata.get("category", "general"),
        )
        meta_group.add(category_row)

        # Author
        author_row = Adw.ActionRow(
            title="Author",
            subtitle=skill_metadata.get("author", "Unknown"),
        )
        meta_group.add(author_row)

        content_box.append(meta_group)

        # Examples
        examples = skill_metadata.get("examples", [])
        if examples:
            examples_group = Adw.PreferencesGroup(title="Example Commands")
            for example in examples:
                row = Adw.ActionRow(title=example)
                examples_group.add(row)
            content_box.append(examples_group)

        # Permissions
        permissions = skill_metadata.get("permissions", [])
        if permissions:
            perm_group = Adw.PreferencesGroup(title="Required Permissions")
            for perm in permissions:
                row = Adw.ActionRow(title=perm)
                perm_group.add(row)
            content_box.append(perm_group)

        content.set_child(content_box)
        box.append(content)

        self.set_content(box)


class NotificationOverlay:
    """
    Toast notification overlay for in-app notifications.
    """

    def __init__(self, parent: Gtk.Window):
        self._parent = parent
        self._overlay = Adw.ToastOverlay()

    def show_toast(self, message: str, action_label: str = None, action_callback: Callable = None):
        """Show a toast notification"""
        toast = Adw.Toast(title=message, timeout=3)

        if action_label and action_callback:
            toast.set_button_label(action_label)
            toast.connect("button-clicked", lambda *_: action_callback())

        self._overlay.add_toast(toast)

    def get_overlay(self) -> Adw.ToastOverlay:
        """Get the toast overlay widget"""
        return self._overlay
