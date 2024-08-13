from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import openai
import os
from dotenv import load_dotenv
import time
from gtts import gTTS
from playsound import playsound

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
JPDB_USERNAME = os.getenv('JPDB_USERNAME')
JPDB_PASSWORD = os.getenv('JPDB_PASSWORD')

def setup_driver():
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return webdriver.Chrome(service=service, options=options)

def login_to_jpdb(driver, username, password):
    try:
        driver.get('https://jpdb.io/login')
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.NAME, 'username')))
        driver.find_element(By.NAME, 'username').send_keys(username)
        driver.find_element(By.NAME, 'password').send_keys(password)
        driver.find_element(By.XPATH, '//input[@type="submit"]').click()
        WebDriverWait(driver, 3).until(EC.url_contains('https://jpdb.io/'))
        print("Login successful")
    except Exception as e:
        print(f"Login failed: {e}")
        driver.save_screenshot("login_error.png")
        raise

def get_due_words(driver):
    try:
        print("Navigating to deck page...")
        driver.get('https://jpdb.io/deck?id=11&show_only=overdue')
        print("Waiting for vocabulary list...")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'vocabulary-list')))
        words = []
        entries = driver.find_elements(By.CLASS_NAME, 'entry.overdue')
        print(f"Found {len(entries)} entries")
        for entry in entries:
            try:
                japanese = entry.find_element(By.CLASS_NAME, 'vocabulary-spelling').text
                meaning_div = entry.find_element(By.XPATH, './div[2]')  # The second div contains the meaning
                meaning = meaning_div.text.split('\n')[0]  # Take the first line as the meaning
                words.append((japanese, meaning))
            except NoSuchElementException as e:
                print(f"Error processing entry: {e}")
        print(f"Processed {len(words)} words")
        return words
    except Exception as e:
        print(f"Error getting due words: {e}")
        driver.save_screenshot("due_words_error.png")
        raise

def generate_short_story(words):
    japanese_words = [word[0] for word in words]
    prompt = f"Create a short story in Japanese that includes the following words: {', '.join(japanese_words)}. Then provide an English translation of the story. PLease break up the english half and japanese half by '@'"
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that creates short stories to help with Japanese language learning."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message['content']

def generate_long_story(words, theme):
    japanese_words = [word[0] for word in words]
    prompt = f"Create a long story in Japanese, that is about 5 minutes long to read, that includes the following words: {', '.join(japanese_words)}. Make the story follow the theme of {theme}"
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that creates short stories to help with Japanese language learning."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message['content']

def play_audio(text, lang='ja'):
    # Create the 'audio' folder if it doesn't exist
    audio_folder = "audio"
    if not os.path.exists(audio_folder):
        os.makedirs(audio_folder)
    
    # Generate a unique filename based on the first few characters of the text
    filename = f"story_{text[:10].replace(' ', '_')}.mp3"
    file_path = os.path.join(audio_folder, filename)
    
    # Generate and save the audio file
    tts = gTTS(text=text, lang=lang)
    tts.save(file_path)
    
    # Play the audio
    playsound(file_path)

    print(f"Audio saved as: {file_path}")

def main():
    driver = setup_driver()
    try:
        login_to_jpdb(driver, JPDB_USERNAME, JPDB_PASSWORD)
        due_words = get_due_words(driver)
        
        if not due_words:
            print("No due words found. Exiting.")
            return

        long_short = input("Do you want to generate a short(0) or long(1) story?: ")

        if long_short == "0":
            i = 0
            while i < len(due_words):
                words_subset = due_words[i:i+5]
                while True:
                    story = generate_short_story(words_subset)
                    
                    print("\nWords in this set:")
                    for word, meaning in words_subset:
                        print(f"{word}: {meaning}")
                    
                    print("\nHere's a story incorporating the vocabulary:")
                    print(story)

                    
                    japanese_story = story.split('@')[0]
                    # print("1:", japanese_story)
                    
                    print("\nPlaying audio of the story...")
                    play_audio(japanese_story)
                    
                    print("\nEnter 0 to replay audio, 1 to regenerate story, 2 to move to next set, or 'quit' to exit:")
                    user_input = input().lower()
                    
                    if user_input == '0':
                        print("Replaying audio...")
                        play_audio(japanese_story)
                    elif user_input == '1':
                        print("Regenerating story...")
                        continue
                    elif user_input == '2' or user_input == '':
                        print("Moving to next set...")
                        break
                    elif user_input == 'quit':
                        print("Exiting program...")
                        return
                    else:
                        print("Invalid input. Please try again.")
                
                i += 5
            
            print("No more words to review. Exiting.")

        elif long_short == "1":
            theme = input("Input a theme for the story to follow: ")
            story = generate_long_story(due_words, theme)


            
            # print("\nWords in this set:")
            # for word, meaning in due_words:
            #     print(f"{word}: {meaning}")
            
            print("\nHere's a story incorporating the vocabulary:")
            print(story)
            
            print("\nPlaying audio of the story...")
            play_audio(story)

    
    except Exception as e:
        print(f"An error occurred: {e}")
        driver.save_screenshot("error_screenshot.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()