from django.shortcuts import get_object_or_404
from apps.service import serializers as ytpl_serializers
from rest_framework import viewsets
from rest_framework.response import Response

class ListRetrievePeople