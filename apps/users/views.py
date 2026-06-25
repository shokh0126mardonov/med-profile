from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema


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