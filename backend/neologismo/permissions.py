from rest_framework import permissions

# Métodos que não alteram nada e portanto são liberados para leitura pública.
METODOS_SEGUROS = permissions.SAFE_METHODS


class DonoOuStaff(permissions.BasePermission):
    """Escrita só para o autor do verbete ou para a equipe.

    Sem isto, `IsAuthenticatedOrReadOnly` deixaria qualquer usuário logado
    editar ou apagar o verbete de outra pessoa — basta um PUT/DELETE em
    /api/neologismos/<id>/.

    Regras:
    - leitura: liberada (o queryset já esconde o que não é público);
    - staff: pode tudo;
    - autor: pode editar/apagar enquanto o verbete não foi aprovado. Depois de
      aprovado o conteúdo é público e passa a ser editado só pela moderação.
    """

    message = 'Você só pode alterar verbetes seus que ainda não foram aprovados.'

    def has_object_permission(self, request, view, obj):
        if request.method in METODOS_SEGUROS:
            return True

        if request.user.is_staff:
            return True

        if obj.autor_id != request.user.id:
            return False

        return obj.status != 'aprovado'
