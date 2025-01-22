import json
import os
import re
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from pytubefix import YouTube
import assemblyai as aai
import google.generativeai as genai
from urllib.request import Request, urlopen
from .models import BlogPost

req = Request(
    url='http://www.youtube.com', 
    headers={'User-Agent': 'Mozilla/5.0'}
)
webpage = urlopen(req).read()

# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)
        
        title = yt_title(yt_link)

        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error': "Failed to get transcript"}, status=500)
        
        blog_content = generate_blog_from_transcription(transcription)

        if not blog_content:
            return JsonResponse({'error': "Failed to generate blog article"}, status=500)
        
        new_blog_article = BlogPost.objects.create(
            user= request.user,
            youtube_title= title,
            youtube_link= yt_link,
            generated_content= blog_content
        )

        new_blog_article.save()
        
        return JsonResponse({'content':blog_content})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def yt_title(link):
    yt = YouTube(link, 'WEB')
    title = yt.title
    return title

def download_audio(link):
    yt = YouTube(link, 'WEB')
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file

def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = '7e0c2354c51b4feea02f767094699765'

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    return transcript.text

def generate_blog_from_transcription(transcription):
    genai.configure(api_key='AIzaSyC-l6LVFUOYBPGvA8FH1cP_CIH1kwApBBU')

    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article, write it based on the transcript, but do not make it look like a YouTube video, make it look like a proper blog article:\n\n{transcription}\n\nArticle: answer should also be less than 200 words"
    generated_content = model.generate_content(
        prompt
    )
    
    return (generated_content.text)

def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, 'all-blogs.html', {'blog_articles': blog_articles})

def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail':blog_article_detail})
    else:
        return redirect('/')

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = 'Invalid username or password'
            return render(request, 'login.html', {'error_message':error_message})
    return render(request, 'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatpassword = request.POST['repeatpassword']

        if password == repeatpassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error creating account'
                return render(request, 'signup.html', {'error_message': error_message})
        else:
            error_message = 'Password do not match'
            return render(request, 'signup.html', {'error_message': error_message})
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')


