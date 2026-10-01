from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

Usuario = get_user_model()


class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'password', 'is_admin']
        read_only_fields = ['is_admin']
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True},
        }

    def validate_username(self, value):
        username = value.strip()
        if len(username) < 3:
            raise serializers.ValidationError(
                'O nome de usuário precisa ter ao menos 3 caracteres.'
            )
        # A checagem é case-insensitive para não existirem "Joao" e "joao"
        # como contas diferentes.
        if Usuario.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError('Este nome de usuário já está em uso.')
        return username

    def validate_email(self, value):
        email = value.strip().lower()
        if email and Usuario.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Este e-mail já está cadastrado.')
        return email

    def validate_password(self, value):
        # Aplica os AUTH_PASSWORD_VALIDATORS (tamanho mínimo, senha comum,
        # senha só de números). Antes o serializer só checava min_length=6.
        try:
            validate_password(value)
        except DjangoValidationError as erro:
            raise serializers.ValidationError(list(erro.messages)) from erro
        return value

    def create(self, validated_data):
        return Usuario.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )


class UsuarioSerializer(serializers.ModelSerializer):
    total_enviados = serializers.SerializerMethodField()
    total_aprovados = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'is_admin', 'is_staff',
            'date_joined', 'total_enviados', 'total_aprovados',
        ]
        read_only_fields = fields

    def get_total_enviados(self, obj) -> int:
        return obj.meus_neologismos.count()

    def get_total_aprovados(self, obj) -> int:
        return obj.meus_neologismos.filter(status='aprovado').count()


class SessaoSerializer(serializers.Serializer):
    """Resposta de login e cadastro."""

    token = serializers.CharField()
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    is_admin = serializers.BooleanField()


class RecuperarSenhaSerializer(serializers.Serializer):
    """Pedido de recuperação: recebe só o e-mail."""

    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class RedefinirSenhaSerializer(serializers.Serializer):
    """Confirmação da redefinição, com o uid e o token vindos do link."""

    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )

    def validate(self, dados):
        # O uid é o pk do usuário em base64 (padrão do Django). Decodificamos
        # aqui para validar a senha contra os atributos do usuário certo —
        # UserAttributeSimilarityValidator precisa da instância.
        try:
            pk = urlsafe_base64_decode(dados['uid']).decode()
            usuario = Usuario.objects.get(pk=pk)
        except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist) as erro:
            # `from erro` preserva a causa no traceback: um uid corrompido e
            # um usuário apagado chegam aqui pelo mesmo caminho, e no log a
            # diferença importa.
            raise serializers.ValidationError(
                {'uid': 'Link inválido. Peça uma nova recuperação de senha.'}
            ) from erro

        if not default_token_generator.check_token(usuario, dados['token']):
            raise serializers.ValidationError({
                'token': 'Este link expirou ou já foi usado. '
                         'Peça uma nova recuperação de senha.'
            })

        try:
            validate_password(dados['password'], user=usuario)
        except DjangoValidationError as erro:
            raise serializers.ValidationError(
                {'password': list(erro.messages)}
            ) from erro

        dados['usuario'] = usuario
        return dados
