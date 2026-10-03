#include <SDL3/SDL.h>
#include <stdio.h>
#include <string.h>

static void SDLCALL silence(void *userdata, SDL_AudioStream *stream, int additional, int total)
{
    static const unsigned char zeros[8192];
    (void)userdata;
    (void)total;
    while (additional > 0) {
        int length = additional < (int)sizeof(zeros) ? additional : (int)sizeof(zeros);
        if (!SDL_PutAudioStreamData(stream, zeros, length)) break;
        additional -= length;
    }
}

int main(void)
{
    SDL_AudioSpec spec = {SDL_AUDIO_F32, 2, 48000}, actual;
    int frames;
    if (!SDL_Init(SDL_INIT_AUDIO)) {
        fprintf(stderr, "%s\n", SDL_GetError());
        return 1;
    }
    SDL_AudioStream *stream = SDL_OpenAudioDeviceStream(SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK, &spec, silence, NULL);
    if (!stream) {
        fprintf(stderr, "%s\n", SDL_GetError());
        return 2;
    }
    SDL_GetAudioDeviceFormat(SDL_GetAudioStreamDevice(stream), &actual, &frames);
    printf("driver=%s rate=%d channels=%d format=%x frames=%d\n",
           SDL_GetCurrentAudioDriver(), actual.freq, actual.channels, actual.format, frames);
    fflush(stdout);
    SDL_ResumeAudioStreamDevice(stream);
    SDL_Delay(10000);
    SDL_DestroyAudioStream(stream);
    SDL_Quit();
    return 0;
}
