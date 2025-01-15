from rest_framework import serializers
from apps.activity.models import Job,Jobneed,JobneedDetails,Question,QuestionSet,QuestionSetBelonging

class JobSerializers(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = '__all__'


class JobneedSerializers(serializers.ModelSerializer):
    class Meta:
        model = Jobneed
        fields = '__all__'


class JobneedDetailsSerializers(serializers.ModelSerializer):
    class Meta:
        model = JobneedDetails
        fields = '__all__'


class QuestionSerializers(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'


class QuestionSetSerializers(serializers.ModelSerializer):
    class Meta:
        model = QuestionSet
        fields = '__all__'


class QuestionSetBelongingSerializers(serializers.ModelSerializer):
    class Meta:
        model = QuestionSetBelonging
        fields = '__all__'
