from rest_framework import serializers

from .models import Contexto, Neologismo

# Um verbete não precisa de mais que isso, e o limite evita que um POST
# gigante trave o banco.
MAX_TAGS = 8
MAX_CONTEXTOS = 10


class ContextoSerializer(serializers.ModelSerializer):
    # allow_blank: citações vazias chegam do formulário e são descartadas em
    # NeologismoSerializer.validate_contextos, em vez de reprovar o envio.
    citacao = serializers.CharField(allow_blank=True)
    fonte = serializers.CharField(max_length=200, allow_blank=True, required=False)
    link = serializers.URLField(max_length=500, allow_blank=True, required=False)

    class Meta:
        model = Contexto
        fields = ['id', 'citacao', 'fonte', 'link']


class NeologismoSerializer(serializers.ModelSerializer):
    autor_nome = serializers.ReadOnlyField(source='autor.username')

    # Preenchidos pelas anotações do queryset (ver NeologismoViewSet). O
    # fallback para o método do model cobre quem serializa um objeto solto,
    # como no retorno de uma ação de moderação.
    total_likes = serializers.SerializerMethodField()
    curtido_por_mim = serializers.SerializerMethodField()

    contextos = ContextoSerializer(many=True, required=False)

    tags = serializers.ListField(
        child=serializers.CharField(max_length=50, allow_blank=True),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = Neologismo
        fields = [
            'id', 'data_registro', 'titulo', 'slug', 'classe_gramatical',
            'tipologia', 'elaborado_por',
            'definicao', 'contexto_uso', 'contextos', 'tags', 'status',
            'motivo_rejeicao', 'reativado_em', 'moderado_em',
            'data_criacao', 'data_atualizacao',
            'autor', 'autor_nome',
            'total_likes', 'curtido_por_mim',
        ]
        # Definidos pelo servidor / por ações dedicadas, nunca pelo cliente.
        read_only_fields = [
            'slug', 'status', 'autor',
            'motivo_rejeicao', 'reativado_em', 'moderado_em',
            'data_criacao', 'data_atualizacao',
        ]

    def get_total_likes(self, obj) -> int:
        anotado = getattr(obj, 'likes_count', None)
        return anotado if anotado is not None else obj.likes.count()

    def get_curtido_por_mim(self, obj) -> bool:
        anotado = getattr(obj, 'curtido_por_mim', None)
        if anotado is not None:
            return bool(anotado)

        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(pk=request.user.pk).exists()

    # --- Validação ---

    def validate_titulo(self, value):
        titulo = ' '.join(value.split())
        if len(titulo) < 2:
            raise serializers.ValidationError(
                'O título precisa ter ao menos 2 caracteres.'
            )
        return titulo

    def validate_definicao(self, value):
        definicao = value.strip()
        if len(definicao) < 10:
            raise serializers.ValidationError(
                'Descreva o significado com ao menos 10 caracteres.'
            )
        return definicao

    def validate_tags(self, value):
        # Normaliza (tira espaços, remove vazias) e deduplica preservando a
        # ordem, para não gravar ["Gíria", "gíria ", "Gíria"].
        vistas = set()
        limpas = []
        for tag in value:
            tag = ' '.join(tag.split())
            if not tag:
                continue
            chave = tag.casefold()
            if chave in vistas:
                continue
            vistas.add(chave)
            limpas.append(tag)

        if len(limpas) > MAX_TAGS:
            raise serializers.ValidationError(
                f'Use no máximo {MAX_TAGS} tags.'
            )
        return limpas

    def validate_contextos(self, value):
        if len(value) > MAX_CONTEXTOS:
            raise serializers.ValidationError(
                f'Envie no máximo {MAX_CONTEXTOS} citações.'
            )
        # Descarta citações em branco em vez de gravar linhas vazias.
        return [c for c in value if c.get('citacao', '').strip()]

    # --- Escrita aninhada ---

    def create(self, validated_data):
        contextos_data = validated_data.pop('contextos', [])
        neologismo = Neologismo.objects.create(**validated_data)
        Contexto.objects.bulk_create([
            Contexto(neologismo=neologismo, **contexto)
            for contexto in contextos_data
        ])
        return neologismo

    def update(self, instance, validated_data):
        contextos_data = validated_data.pop('contextos', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        # Se o cliente enviou contextos, substitui os existentes.
        if contextos_data is not None:
            instance.contextos.all().delete()
            Contexto.objects.bulk_create([
                Contexto(neologismo=instance, **contexto)
                for contexto in contextos_data
            ])
        return instance


class NeologismoModeracaoSerializer(NeologismoSerializer):
    """Versão usada pelo painel admin, com os sinais internos de moderação."""

    total_deslikes = serializers.SerializerMethodField()
    autor_email = serializers.ReadOnlyField(source='autor.email')
    moderado_por_nome = serializers.ReadOnlyField(source='moderado_por.username')

    class Meta(NeologismoSerializer.Meta):
        fields = NeologismoSerializer.Meta.fields + [
            'total_deslikes', 'autor_email', 'moderado_por_nome',
        ]

    def get_total_deslikes(self, obj) -> int:
        anotado = getattr(obj, 'deslikes_count', None)
        return anotado if anotado is not None else obj.deslikes.count()


class RejeicaoSerializer(serializers.Serializer):
    """Corpo esperado por POST /api/neologismos/<id>/rejeitar/."""

    motivo_rejeicao = serializers.CharField(
        min_length=5,
        max_length=1000,
        help_text='Explique ao autor por que o verbete foi rejeitado.',
    )


class CurtidaRespostaSerializer(serializers.Serializer):
    """Corpo devolvido por POST /api/neologismos/<id>/curtir/."""

    id = serializers.IntegerField()
    curtido_por_mim = serializers.BooleanField()
    total_likes = serializers.IntegerField()
