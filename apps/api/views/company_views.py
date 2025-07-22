# -*- coding: utf-8 -*-
import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from apps.companies.models import Company
from apps.api.serializers.company_serializers import CompanySerializer

logger = logging.getLogger(__name__)

class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    
    def get_queryset(self):
        from apps.api.user_company_helper import get_user_companies_exact
        user = self.request.user
        companies = get_user_companies_exact(user)
        logger.error(f"🔥🔥🔥 NUCLEAR: User {user.username} = {companies.count()} companies")
        return companies
    
    def retrieve(self, request, *args, **kwargs):
        from apps.api.user_company_helper import get_user_companies_exact
        company_id = kwargs.get("pk")
        
        try:
            company_id = int(company_id)
        except:
            return Response({"error": "Invalid ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        user_companies = get_user_companies_exact(request.user)
        user_company_ids = [c.id for c in user_companies]
        
        logger.error(f"🔥🔥🔥 NUCLEAR ACCESS: {request.user.username} -> {company_id}")
        
        if company_id not in user_company_ids:
            logger.error(f"🚨🚨🚨 NUCLEAR BLOCK: {company_id} BLOCKED")
            return Response({
                "error": "NUCLEAR_BLOCK",
                "message": "Access denied",
                "user": request.user.username,
                "company_requested": company_id,
                "companies_allowed": user_company_ids
            }, status=status.HTTP_403_FORBIDDEN)
        
        return super().retrieve(request, *args, **kwargs)