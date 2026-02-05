# -*- coding: utf-8 -*-
"""
Helper JWT COMPLETAMENTE CORREGIDO para relación User-Company específica de VENDO_SRI
"""

import logging
from apps.companies.models import Company

logger = logging.getLogger(__name__)


def get_user_companies_exact(user):
    """
    Función ESPECÍFICA CORREGIDA para tu modelo de User-Company
    """
    if not user or not user.is_authenticated:
        logger.warning("❌ User not authenticated")
        return Company.objects.none()
    
    # ✅ NUEVO: Detectar VirtualCompanyUser (tokens VSR de empresa)
    from apps.api.authentication import VirtualCompanyUser
    if isinstance(user, VirtualCompanyUser):
        # VirtualCompanyUser ya tiene su empresa asignada directamente
        logger.info(f"✅ VirtualCompanyUser accessing company {user.company.id}")
        return Company.objects.filter(id=user.company.id, is_active=True)
    
    if user.is_superuser:
        logger.info(f"✅ Superuser {user.username} accessing all companies")
        return Company.objects.filter(is_active=True)
    
    # Método 1: UserCompanyAssignment (CORREGIDO)
    try:
        from apps.users.models import UserCompanyAssignment
        assignment = UserCompanyAssignment.objects.get(user=user)
        
        if assignment.is_assigned():
            companies = assignment.get_assigned_companies().filter(is_active=True)
            logger.info(f"✅ Assignment method: User {user.username} has {companies.count()} assigned companies")
            return companies
        else:
            logger.warning(f"❌ User {user.username} is in waiting room - status: {assignment.status}")
            return Company.objects.none()
            
    except ImportError:
        logger.debug("UserCompanyAssignment not available, using direct relationship")
    except UserCompanyAssignment.DoesNotExist:
        logger.debug(f"No UserCompanyAssignment found for user {user.username}, using direct relationship")
    except Exception as e:
        logger.error(f"Error with UserCompanyAssignment for user {user.username}: {e}")
    
    # Método 2: Relación directa User.company (ForeignKey)
    try:
        if hasattr(user, 'company') and user.company and user.company.is_active:
            companies = Company.objects.filter(id=user.company.id, is_active=True)
            logger.info(f"✅ Direct method: User {user.username} has company {user.company.id}")
            return companies
    except Exception as e:
        logger.debug(f"Direct company method failed for user {user.username}: {e}")
    
    # Si no tiene empresa asignada
    logger.warning(f"❌ User {user.username} has no company assigned")
    return Company.objects.none()


def get_user_company_by_id_exact(company_id, user):
    """
    Función ESPECÍFICA para obtener una empresa por ID si el usuario tiene acceso
    """
    if not user or not user.is_authenticated:
        logger.warning("❌ User not authenticated")
        return None
    
    # ✅ NUEVO: VirtualCompanyUser - validar acceso directo
    from apps.api.authentication import VirtualCompanyUser
    if isinstance(user, VirtualCompanyUser):
        try:
            company_id = int(company_id)
            if user.company.id == company_id and user.company.is_active:
                logger.info(f"✅ VirtualCompanyUser has access to company {company_id}")
                return user.company
            else:
                logger.warning(f"❌ VirtualCompanyUser denied access to company {company_id}")
                return None
        except (ValueError, TypeError):
            logger.error(f"Invalid company_id format: {company_id}")
            return None
    
    try:
        company_id = int(company_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid company_id format: {company_id}")
        return None
    
    if user.is_superuser:
        try:
            company = Company.objects.get(id=company_id, is_active=True)
            logger.info(f"✅ Superuser {user.username} accessing company {company_id}")
            return company
        except Company.DoesNotExist:
            logger.warning(f"❌ Company {company_id} does not exist")
            return None
    
    # Obtener empresas del usuario y verificar si tiene acceso a la solicitada
    user_companies = get_user_companies_exact(user)
    company = user_companies.filter(id=company_id).first()
    
    if company:
        logger.info(f"✅ User {user.username} has access to company {company_id}")
    else:
        logger.warning(f"❌ User {user.username} denied access to company {company_id}")
    
    return company


# ========== SISTEMA JWT PARA COMPANY TOKENS ==========

import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone

# Configuración JWT
JWT_SECRET = getattr(settings, 'SECRET_KEY', 'fallback-secret-key')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24


class CompanyJWTManager:
    """Gestor de tokens JWT para empresas"""
    
    @staticmethod
    def generate_company_token(company_id, user_id, user_email=None):
        """Genera token JWT para empresa específica y usuario"""
        now = timezone.now()
        expiration = now + timedelta(hours=JWT_EXPIRATION_HOURS)
        
        payload = {
            'company_id': int(company_id),
            'user_id': int(user_id),
            'user_email': user_email,
            'iat': now.timestamp(),
            'exp': expiration.timestamp(),
            'iss': 'vendo-sri-system',
            'type': 'company_access'
        }
        
        try:
            token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
            logger.info(f"🔐 JWT token generated for user {user_id}, company {company_id}")
            return token
        except Exception as e:
            logger.error(f"❌ Error generating JWT token: {str(e)}")
            return None
    
    @staticmethod
    def validate_company_token(token, user_id):
        """Valida token JWT y devuelve company_id si es válido"""
        if not token or not user_id:
            logger.warning("❌ Token or user_id missing")
            return None
        
        try:
            # Decodificar token
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            
            # Validaciones de seguridad
            if payload.get('type') != 'company_access':
                logger.warning(f"❌ Invalid token type: {payload.get('type')}")
                return None
            
            if payload.get('user_id') != int(user_id):
                logger.warning(f"❌ Token user_id mismatch: {payload.get('user_id')} vs {user_id}")
                return None
            
            if payload.get('iss') != 'vendo-sri-system':
                logger.warning(f"❌ Invalid token issuer: {payload.get('iss')}")
                return None
            
            company_id = payload.get('company_id')
            logger.info(f"✅ JWT token validated for user {user_id}, company {company_id}")
            return company_id
            
        except jwt.ExpiredSignatureError:
            logger.warning("❌ JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"❌ JWT token invalid: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Error validating JWT token: {str(e)}")
            return None
    
    @staticmethod
    def get_company_from_jwt_token(token, user):
        """Obtiene empresa desde token JWT validando usuario y permisos"""
        if not user or not user.is_authenticated:
            logger.warning("❌ User not authenticated")
            return None
        
        # ✅ NUEVO: VirtualCompanyUser no necesita validar JWT
        from apps.api.authentication import VirtualCompanyUser
        if isinstance(user, VirtualCompanyUser):
            logger.info(f"✅ VirtualCompanyUser bypasses JWT validation")
            return None  # No aplica JWT para VirtualCompanyUser
        
        # Validar token y obtener company_id
        company_id = CompanyJWTManager.validate_company_token(token, user.id)
        
        if not company_id:
            return None
        
        try:
            # Verificar que la empresa existe
            company = Company.objects.get(id=company_id, is_active=True)
            
            # Verificar que el usuario tiene acceso a esa empresa
            user_companies = get_user_companies_exact(user)
            
            if user_companies.filter(id=company_id).exists():
                logger.info(f"✅ JWT: User {user.username} has valid access to company {company_id}")
                return company
            else:
                logger.warning(f"❌ JWT: User {user.username} has no access to company {company_id}")
                return None
                
        except Company.DoesNotExist:
            logger.warning(f"❌ JWT: Company {company_id} does not exist")
            return None
    
    @staticmethod
    def generate_user_company_tokens(user):
        """Genera tokens JWT para todas las empresas del usuario"""
        if not user or not user.is_authenticated:
            return {}
        
        # ✅ NUEVO: VirtualCompanyUser no genera JWT tokens
        from apps.api.authentication import VirtualCompanyUser
        if isinstance(user, VirtualCompanyUser):
            logger.info(f"✅ VirtualCompanyUser doesn't need JWT tokens")
            return {}
        
        try:
            user_companies = get_user_companies_exact(user)
            tokens = {}
            
            expiration = timezone.now() + timedelta(hours=JWT_EXPIRATION_HOURS)
            
            for company in user_companies:
                token = CompanyJWTManager.generate_company_token(
                    company.id, 
                    user.id, 
                    user.email
                )
                
                if token:
                    tokens[str(company.id)] = {
                        'token': token,
                        'company_name': company.business_name,
                        'company_id': company.id,
                        'expires_at': expiration.strftime('%Y-%m-%d %H:%M:%S')
                    }
            
            logger.info(f"🔐 Generated {len(tokens)} JWT tokens for user {user.username}")
            return tokens
            
        except Exception as e:
            logger.error(f"❌ Error generating JWT tokens for user {user.username}: {str(e)}")
            return {}


# ========== FUNCIONES DE CONVENIENCIA ==========

def get_user_company_by_jwt_token(jwt_token, user):
    """Obtiene empresa usando token JWT - MÉTODO PRINCIPAL"""
    if not user or not user.is_authenticated:
        logger.warning('❌ User not authenticated for JWT')
        return None
    
    if not jwt_token:
        logger.warning('❌ No JWT token provided')
        return None
    
    try:
        company = CompanyJWTManager.get_company_from_jwt_token(jwt_token, user)
        if company:
            logger.info(f'✅ JWT: User {user.username} validated for company {company.id}')
        else:
            logger.warning(f'❌ JWT: Invalid token for user {user.username}')
        return company
    except Exception as e:
        logger.error(f'❌ JWT error for user {user.username}: {str(e)}')
        return None


def generate_user_jwt_tokens(user):
    """Genera tokens JWT para todas las empresas del usuario"""
    try:
        return CompanyJWTManager.generate_user_company_tokens(user)
    except Exception as e:
        logger.error(f'Error generating JWT tokens: {str(e)}')
        return {}


def get_user_company_by_id_or_token(company_param, user):
    """
    Función HÍBRIDA: intenta JWT primero, luego ID (backward compatibility)
    """
    if not user or not user.is_authenticated:
        return None
    
    if not company_param:
        return None
    
    # Intentar primero como token JWT (tokens son largos)
    if len(str(company_param)) > 10:
        company = get_user_company_by_jwt_token(company_param, user)
        if company:
            logger.info(f"✅ JWT method worked for user {user.username}")
            return company
    
    # Si no funciona como JWT, intentar como ID (backward compatibility)
    try:
        company_id = int(company_param)
        company = get_user_company_by_id_exact(company_id, user)
        if company:
            logger.info(f"✅ ID method worked for user {user.username}")
        return company
    except (ValueError, TypeError):
        logger.warning(f"❌ Invalid company parameter: {company_param}")
        return None


def debug_user_exact_relationship(user):
    """Función de debugging específica para tu modelo"""
    if not user:
        return "No user provided"
    
    # ✅ NUEVO: Información especial para VirtualCompanyUser
    from apps.api.authentication import VirtualCompanyUser
    if isinstance(user, VirtualCompanyUser):
        return {
            'user_type': 'VirtualCompanyUser',
            'company_id': user.company.id,
            'company_name': user.company.business_name,
            'is_authenticated': user.is_authenticated,
            'access_method': 'company_api_token'
        }
    
    debug_info = {
        'user_type': 'Django User',
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'is_superuser': user.is_superuser,
        'direct_company': None,
        'assigned_companies': [],
        'total_accessible_companies': 0,
        'access_method': None
    }
    
    # Verificar relación directa User.company
    if hasattr(user, 'company') and user.company:
        debug_info['direct_company'] = {
            'id': user.company.id,
            'name': user.company.business_name,
            'is_active': user.company.is_active
        }
        debug_info['access_method'] = 'direct_company'
    
    # Verificar UserCompanyAssignment
    try:
        from apps.users.models import UserCompanyAssignment
        assignment = UserCompanyAssignment.objects.get(user=user)
        assigned = assignment.get_assigned_companies()
        debug_info['assigned_companies'] = [
            {
                'id': company.id,
                'name': company.business_name,
                'is_active': company.is_active
            }
            for company in assigned
        ]
        debug_info['assignment_status'] = assignment.status
        if assignment.is_assigned() and assigned.exists():
            debug_info['access_method'] = 'assignment_system'
    except Exception as e:
        debug_info['assignment_status'] = f'error: {str(e)}'
    
    # Contar empresas accesibles
    try:
        accessible = get_user_companies_exact(user)
        debug_info['total_accessible_companies'] = accessible.count()
    except Exception as e:
        debug_info['total_accessible_companies'] = f'error: {str(e)}'
    
    return debug_info