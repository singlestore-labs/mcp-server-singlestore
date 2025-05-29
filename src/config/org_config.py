from typing import Optional


class OrganizationConfig:
    """Organization configuration class that stores organization-related information."""

    def __init__(
        self,
        organization_id: Optional[str] = None,
        organization_name: Optional[str] = None,
    ):
        self._organization_id = organization_id
        self._organization_name = organization_name

    @property
    def organization_id(self) -> Optional[str]:
        return self._organization_id

    @organization_id.setter
    def organization_id(self, value: Optional[str]):
        self._organization_id = value

    @property
    def organization_name(self) -> Optional[str]:
        return self._organization_name

    @organization_name.setter
    def organization_name(self, value: Optional[str]):
        self._organization_name = value

    def set_organization(self, org_id: str, org_name: str):
        self._organization_id = org_id
        self._organization_name = org_name

    def get_organization(self) -> Optional[tuple[str]]:
        return self._organization_id, self._organization_name

    def clear_organization(self):
        self._organization_id = None
        self._organization_name = None

    def is_organization_selected(self) -> bool:
        return self._organization_id is not None
