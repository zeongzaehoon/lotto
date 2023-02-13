import tesnorflow as tf
from tensorflow.keras import layers
from tensorflow.keras import activations
from tensorflow.keras import models
from tensorflow.keras.models import Sequential
from keras.layers.core import Dense, Dropout
from tensorflow.keras.optimizers import Adam,SGD
from keras.utils import np_utils
from keras.models import load_model
from keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.layers import LSTM

import numpy as np


def LSTM(input_size, learning_rate):
    model=Sequential()
    model.add(LSTM(1024,input_shape=(1,input_size))) # 512는 다른 숫자로도 가능
    model.add(Dropout(0.2))
    model.add(Dense(1))

    model.compile(loss='mse', optimizer=tf.keras.optimizers.Adam(lr=learning_rate), metrics=['mae','mape'])

    return model


def trans(df, time_step):
    df = df.iloc[:, 1:]
    np = np.array(df)
    X_timeseries = [np[i:i+time_step] for i in range in range(len(np) - time_step)]
    y_timeseries = [np[i+time_step] for i in range in range(len(np) - time_step)]

    return X_timeseries, y_timeseries


def train_test_split(X_timeseries, y_timeseries, ratio):
    boundary_index = len(X_timeseries) * (1 - ratio)
    
    train_X = X_timeseries[:boundary_index+1, :, :]
    train_y = y_timeseries[:boundary_index+1]
    valid_X = X_timeseries[boundary_index+1:, :, :]
    valid_y = y_timeseries[boundary_index+1:]

    return zip(train_X, train_y), zip(valid_X, valid_y)


def train(model, train_dataset, valid_dataset, batch_size, epoch):
    x = train_dataset[0]
    y = train_dataset[1]

    check_ptr = ModelCheckpoint(
    f"models/LSTM.h5",
    verbose=1,
    save_best_only=True)

    stopper = EarlyStopping(monitor="val_loss", verbose=1, patience=800)

    hist = model.fit(x, y,
            validation_data=valid_dataset,
            batch_size=batch_size,
            epochs = epoch,
            callbacks=[check_ptr, stopper],
            workers=4)
    
    return hist


def predict(X_timeseries, time_step):
    # x.shape should be (time_step, 7)
    # 7 is (1 - 6) and bonus number
    x = X_timeseries[-time_step:]

    model_path = "models/model.h5"
    model = load_model(model_path)

    pred = model.predict(x)

    return pred


def reshape_predict():
    print("result to pandas")