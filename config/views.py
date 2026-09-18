from django.http import HttpResponse


def home(request):
    return HttpResponse(
        """
        <main style="font-family: sans-serif; max-width: 720px; margin: 80px auto;">
            <h1>Authkits Django Test App</h1>
            <p>Authkits is installed and the Django integration is running.</p>
        </main>
        """
    )