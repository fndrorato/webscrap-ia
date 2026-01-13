import json
import os
import sys
import django
import io
import contextlib

# Adicionar o diretório 'backend' ao sys.path para que Django possa encontrar 'app.settings'
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

os.environ['SKIP_ORACLE_INIT'] = 'true'

from django.core.management.base import BaseCommand
from rest_framework.test import APIRequestFactory
from rest_framework import status

from products.views import nissei_search_detailed # Importe sua função aqui

class Command(BaseCommand):
    help = 'Testa a função nissei_search_detailed com parâmetros simulados.'

    def add_arguments(self, parser):
        parser.add_argument('--query', type=str, default='celular',
                            help='Termo de busca para nissei_search_detailed.')
        parser.add_argument('--max_results', type=int, default=20,
                            help='Máximo de resultados a buscar.')
        parser.add_argument('--max_detailed', type=int, default=5,
                            help='Máximo de produtos para detalhar.')
        parser.add_argument('--max_images', type=int, default=3,
                            help='Máximo de imagens por produto.')
        parser.add_argument('--ai_config', type=str, default='none',
                            help='Configuração de IA (e.g., "auto", "none").')
        parser.add_argument('--enhanced_extraction', type=bool, default=True,
                            help='Ativar extração aprimorada.')
        parser.add_argument('--output_file', type=str,
                            help='Caminho para o arquivo onde a saída completa será gravada.')

    def handle(self, *args, **options):
        output_file_path = options.get('output_file')
        
        if output_file_path:
            output_file = open(output_file_path, 'w', encoding='utf-8')
            self.stdout = output_file # Redirecionar self.stdout para o arquivo
        else:
            output_file = None

        try:
            self.stdout.write(self.style.SUCCESS('Iniciando teste da função nissei_search_detailed...'))

            # 1. Simular um request POST
            factory = APIRequestFactory()
            
            # Coletar os argumentos passados para o comando
            query = options['query']
            max_results = options['max_results']
            max_detailed = options['max_detailed']
            max_images = options['max_images']
            ai_config = options['ai_config']
            enhanced_extraction = options['enhanced_extraction']

            data = {
                'query': query,
                'max_results': max_results,
                'max_detailed': max_detailed,
                'max_images': max_images,
                'ai_config': ai_config,
                'enhanced_extraction': enhanced_extraction,
            }
            
            # Criar um request POST simulado
            request = factory.post('/fake-url/', data, format='json')

            # Adicionar um usuário autenticado simulado (necessário devido a @permission_classes([IsAuthenticated]))
            # Para um teste simples, podemos simular um usuário. Em um teste real, você usaria um UserFactory.
            from django.contrib.auth.models import User
            from rest_framework_simplejwt.tokens import RefreshToken
            from rest_framework_simplejwt.authentication import JWTAuthentication

            try:
                user = User.objects.get(username='testuser')
            except User.DoesNotExist:
                user = User.objects.create_user(username='testuser', email='test@example.com', password='password')

            # Gerar token JWT para o usuário de teste
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            # Adicionar o token ao cabeçalho de autorização
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'

            # Autenticar o request manualmente
            authenticator = JWTAuthentication()
            try:
                user_auth_tuple = authenticator.authenticate(request)
                if user_auth_tuple:
                    request.user, request.auth = user_auth_tuple
                else:
                    self.stdout.write(self.style.ERROR('Falha na autenticação JWT manual.'))
                    return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Erro durante a autenticação JWT manual: {e}'))
                return

            # Capturar a saída padrão para ver os logs do extrator
            output_capture = io.StringIO()
            with contextlib.redirect_stdout(output_capture):
                try:
                    response = nissei_search_detailed(request)
                    
                    # Imprimir logs capturados
                    self.stdout.write("\n--- Logs do Extrator ---\n")
                    self.stdout.write(output_capture.getvalue())
                    self.stdout.write("\n--- Fim dos Logs do Extrator ---\n")

                    self.stdout.write(f"Raw response data: {response.data}")

                    # 3. Processar a resposta
                    if response.status_code == status.HTTP_200_OK:
                        self.stdout.write(self.style.SUCCESS('Função executada com sucesso!'))
                        self.stdout.write(json.dumps(response.data, indent=2, ensure_ascii=False))
                    else:
                        self.stdout.write(self.style.ERROR(f'Erro na execução da função: {response.status_code}'))
                        self.stdout.write(json.dumps(response.data, indent=2, ensure_ascii=False))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Ocorreu uma exceção: {e}'))

            self.stdout.write(self.style.SUCCESS('Teste da função nissei_search_detailed concluído.'))
        finally:
            if output_file:
                output_file.close()
                self.stdout = sys.__stdout__ # Restaurar self.stdout
