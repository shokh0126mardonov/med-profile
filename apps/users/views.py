from rest_framework.views import APIView
from rest_framework import viewsets,filters
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model


from .serializers import UserSerializer
from .permissions import IsOperatorUser 

User = get_user_model()

from apps.users.models import SickModel


class SickComeViews(APIView):
    @extend_schema(
        request=None, 
        responses={200: dict} 
    )
    def post(self,request:Request,pk)->Response:
        sick = get_object_or_404(SickModel,pk = pk)
        sick.to_come = True
        sick.save() 

        return Response(
            status=status.HTTP_200_OK
        )


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'manage_profile':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated, IsOperatorUser]
            
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None, *args, **kwargs):
        queryset = self.get_queryset()
        user = get_object_or_404(queryset, pk=pk)
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    def update(self, request, pk=None, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='me')
    def manage_profile(self, request):
        user = request.user 

        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)

        elif request.method in ['PUT', 'PATCH']:
            partial = (request.method == 'PATCH')
            serializer = self.get_serializer(user, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)


class LoginView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.user

        if not user.is_active:
            return Response({"detail": "User is not active"}, status=401)

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "role": user.role,
                "id": user.id,
            }
        )


from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import SickModel
from .serializers import SickModelSerializer

@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name='to_come',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Bemor kelgan yoki kelmaganligini filtrlash (true/false yoki 1/0). Bo'sh bo'lsa hammasini qaytaradi.",
                enum=['true', 'false']
            ),
        ]
    )
)
class SickModelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SickModel.objects.all()
    serializer_class = SickModelSerializer
    permission_classes = [IsAuthenticated]  
    filter_backends = [filters.SearchFilter]
    
    search_fields = ['full_name', 'phone']

    def get_queryset(self):
        queryset = SickModel.objects.all()        
        to_come_param = self.request.query_params.get('to_come', None)
        
        if to_come_param is not None:
            if to_come_param.lower() in ['true']:
                queryset = queryset.filter(to_come=True)
            elif to_come_param.lower() in ['false']:
                queryset = queryset.filter(to_come=False)
                
        return queryset