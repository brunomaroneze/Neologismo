from rest_framework import serializers
from .models import Neologismo, Contexto


class ContextoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contexto
        fields = ['id', 'citacao', 'fonte', 'link']


class NeologismoSerializer(serializers.ModelSerializer):
    # Campos extras para facilitar a vida do Frontend
    autor_nome = serializers.ReadOnlyField(source='autor.username')
    total_likes = serializers.SerializerMethodField()
    total_deslikes = serializers.SerializerMethodField()
    # Citações estruturadas (escrita aninhada no create/update)
    contextos = ContextoSerializer(many=True, required=False)

    class Meta:
        model = Neologismo
        fields = [
            'id', 'data_registro', 'titulo', 'classe_gramatical',
            'tipologia', 'elaborado_por',
            'definicao', 'contexto_uso', 'contextos', 'tags', 'status',
            'motivo_rejeicao', 'reativado_em',
            'data_criacao', 'autor', 'autor_nome',
            'likes', 'deslikes', 'total_likes', 'total_deslikes'
        ]
        # Definidos pelo servidor / por ações dedicadas, nunca pelo cliente.
        read_only_fields = [
            'status', 'autor', 'likes', 'deslikes',
            'motivo_rejeicao', 'reativado_em',
        ]

    def get_total_likes(self, obj):
        return obj.likes.count()

    def get_total_deslikes(self, obj):
        return obj.deslikes.count()

    def create(self, validated_data):
        contextos_data = validated_data.pop('contextos', [])
        neologismo = Neologismo.objects.create(**validated_data)
        for contexto in contextos_data:
            Contexto.objects.create(neologismo=neologismo, **contexto)
        return neologismo

    def update(self, instance, validated_data):
        contextos_data = validated_data.pop('contextos', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        # Se o cliente enviou contextos, substitui os existentes.
        if contextos_data is not None:
            instance.contextos.all().delete()
            for contexto in contextos_data:
                Contexto.objects.create(neologismo=instance, **contexto)
        return instance
