import json
import pickle
import numpy as np
import tensorflow as tf
import re
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Embedding, GlobalAveragePooling1D
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.optimizers import Adam

from sklearn.preprocessing import LabelEncoder
import nltk
from sklearn.metrics import classification_report, f1_score, recall_score, precision_score
from sklearn.model_selection import train_test_split
from tensorflow.keras.layers import Dropout

nltk.download('punkt')  
nltk.download('wordnet') 
nltk.download('stopwords') 
nltk.download('punkt_tab') 



lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words("english"))


import unicodedata

def clean_and_lemmatize(text):
    #Türkçe karakterler gibi özel karakterleri, temel Latin harflerine çevirir, ascii harici karakterleri siler,tekrar stringe çevirir

    #tüm harfleri küçültür
    text = text.lower()
    
    # Kesme işaretlerini koruyan regex:
    text = re.sub(r"[^a-zA-Z\s']", "", text)  
    
    #Metni kelimelere ayırır (tokenization)
    words = nltk.word_tokenize(text)

    # lemmatizer.lemmatize(w) → Kelimeleri kök forma çevirir."playing" → "play"
    #w not in stop_words → "the", "is", "and", "in", gibi önemsiz kelimeleri atar.
    words = [lemmatizer.lemmatize(w) for w in words if w not in stop_words]

    # listesindeki kelimeleri boşlukla birleştirerek tek bir string olarak döndürür.
    return " ".join(words)



# intents.json adlı dosya açılır ve içeriği data adlı Python sözlüğüne (dict) dönüştürülür.
with open("intents.json") as file:
    data = json.load(file)

training_sentences = [] #Kullanıcının yazabileceği/söyleyebileceği örnek cümleler 
training_labels = [] #Her cümleye karşılık gelen etiket (niyet/tag).
labels = [] # Tüm benzersiz etiketleri (intent tag’leri) tutar.
responses = [] # Her niyetin olası cevaplarını tutar.


# Pattern'ları işle

#intents.json içindeki her "intent" nesnesi (bir niyet bloğu) sırayla alınır.
for intent in data['intents']:

    #patterns listesindeki cümleler üzerinden dönülür. Bu cümleler kullanıcının söyleyebileceği örnek ifadelerdir.
    for pattern in intent['patterns']:

        #Her pattern (örnek cümle) training_sentences listesine eklenir.
        training_sentences.append(pattern)

        #Bu pattern'e karşılık gelen tag (intent etiketi), training_labels listesine eklenir.
        training_labels.append(intent['tag'])

    #Her intent’in responses listesi (yani olası cevapları), responses listesine eklenir.
    responses.append(intent['responses'])

    #Eğer bu intent’e ait tag daha önce labels listesine eklenmemişse, eklenir.
    if intent['tag'] not in labels:
        labels.append(intent['tag'])



number_of_classes = len(labels)
print("Sınıf Sayısı:", number_of_classes)  #Kaç lanel olduğunu göstermek için 



# LabelEncoder, scikit-learn kütüphanesinden gelir. Metin türündeki sınıf etiketlerini (intent "tag"leri) sayılara çevirmek.
label_encoder = LabelEncoder() #bu listeyi modelin anlayabileceği şekilde sayılara dönüştürür

#`fit()`, hangi etiketin hangi sayıya karşılık geleceğini öğrenir.Örneğin: training_labels = ['thanks', 'goodbye', 'greeting', 'thanks']
#'goodbye' → 0, 'greeting' → 1, 'thanks' → 2
label_encoder.fit(training_labels)

#Artık her etiket, yukarıdaki sözlüğe göre **sayısal forma çevrilir**.
training_labels = label_encoder.transform(training_labels)




# Tokenizer ayarları  Tokenizer label_encoder ın taglere yaptığını patternler için yapar. Her kelimeye sayı verir

vocab_size = 1000 #Eğitim verisinde en sık geçen ilk 1000 kelime tutulur, gerisi atılır

max_len = 20 #Eğer bir cümle 20'den fazla kelime içeriyorsa kesilir, az ise 0'larla doldurulur. Çünkü Sinir ağları sabit uzunlukta girişler bekler.

oov_token = "<OOV>" # Eğitim sırasında karşılaşılmamış bir kelime, test sırasında gelirse `<OOV>` olarak temsil edilir.

embedding_dim = 64 #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


#Bu satırda bir Tokenizer nesnesi oluşturuluyor.
tokenizer = Tokenizer(num_words=vocab_size, oov_token=oov_token) #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

#Tokenizer, training_sentences listesindeki metinleri analiz eder. Her benzersiz kelimeye bir indeks (integer) atar.
# Daha sık geçen kelimeler daha küçük indeks alır.
tokenizer.fit_on_texts(training_sentences)
word_index = tokenizer.word_index

#Bu satırda: training_sentences içindeki cümleleri, her kelimeyi kendi karşılık geldiği sayıya çevirir.
sequences = tokenizer.texts_to_sequences(training_sentences)

#Cümle dizilerini sabit max_len uzunluğuna getirir. Eğer dizinin boyu max_len'den kısaysa: sıfırlarla doldurulur (padding).
# Eğer uzunsa: sonundan kesilir (truncating='post').
padded_sequences = pad_sequences(sequences, truncating='post', maxlen=max_len)


#Veri %80 eğitim, %20 test olarak ayrılıyor. Model sadece X_train ve y_train ile eğitilir. X_test ve y_test daha sonra doğruluk ölçmek için kullanılır.
X_train, X_test, y_train, y_test = train_test_split(
    padded_sequences, training_labels, test_size=0.2, random_state=42
)
# Modeli oluştur



model = Sequential([  

    Embedding(vocab_size, embedding_dim, input_length=max_len),
    GlobalAveragePooling1D(), 
    #Global ortalama vektörünü 128 nöronlu tam bağlantılı katmana gönderir.

     #ReLU (Rectified Linear Unit) aktivasyonu ile doğrusal olmayan öğrenme sağlar. Burada model, anlamsal temsil üzerinde yüksek boyutlu bir öğrenme yapar.
    Dense(128, activation='relu'),
    Dropout(0.2), 
    Dense(64, activation='relu'),
    Dropout(0.2),

    #Sınıflandırma çıktısını üretir. Her nöron bir intent (niyet) sınıfını temsil eder.

#label_encoder.classes_: Örneğin 12 farklı intent varsa, bu katmanda 12 nöron olur.

 # softmax: Bütün nöronların çıktısını [0,1] aralığına çeker ve toplamlarını 1 yapar → olasılık dağılımı üretir.

    Dense(len(label_encoder.classes_), activation='softmax')
])

#### Çoktan aza doğru gitmek, modelin karar verirken daha rafine (ayırt edici) özellikleri öğrenmesini sağlar.

# Modeli derle
# Modeli derle
model.compile(loss='sparse_categorical_crossentropy', optimizer="adam", metrics=["accuracy"])  # Adam() şeklinde düzeltildi
# Model özeti
model.summary()

# Eğitimi başlat
history = model.fit(X_train, np.array(y_train), epochs=250)

# Tahmin yap
y_pred_probs = model.predict(X_test)
y_pred = np.argmax(y_pred_probs, axis=1)

# Sadece kullanılan sınıflar
used_labels = np.unique(np.concatenate((y_test, y_pred)))
target_names = label_encoder.inverse_transform(used_labels)

# Classification report
print("\nClassification Report:\n")
print(classification_report(
    y_test, y_pred,
    labels=used_labels,
    target_names=target_names
))

# Ek metrikler
print("F1 Score:", round(f1_score(y_test, y_pred, average='weighted'), 4))
print("Recall:", round(recall_score(y_test, y_pred, average='weighted'), 4))
print("Precision:", round(precision_score(y_test, y_pred, average='weighted'), 4))


# Modeli ve yardımcı nesneleri kaydet
model.save("chat_model.h5")

with open("tokenizer.pkl", "wb") as f:
    pickle.dump(tokenizer, f, protocol=pickle.HIGHEST_PROTOCOL)

with open("label_encoder.pkl", "wb") as encoder_file:
    pickle.dump(label_encoder, encoder_file, protocol=pickle.HIGHEST_PROTOCOL)