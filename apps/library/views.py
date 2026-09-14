from rest_framework import permissions, viewsets

from common.permissions import IsAdminOrTeacher

from .models import LibraryMaterial
from .serializers import LibraryMaterialSerializer


class LibraryMaterialViewSet(viewsets.ModelViewSet):
    queryset = LibraryMaterial.objects.select_related("subject", "uploaded_by")
    serializer_class = LibraryMaterialSerializer
    search_fields = ["title", "author"]
    filterset_fields = ["subject", "material_type"]

    def get_permissions(self):
        if self.request.method not in permissions.SAFE_METHODS:
            return [IsAdminOrTeacher()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
