# keras functions for building NNs
from keras.layers import Input, Dense, merge, Lambda, Merge, Activation
from keras.models import Sequential, Model
from keras import backend as K
# kaos functions for distributions
from kaos.layers import BatchNormalization
from kaos.distributions import Distribution as Dist
from kaos.distributions import gaussian_sampler
from kaos.callbacks import NegativeLogLikelihood, LossLog
from kaos.utils import file_handle, Session
from models import VAE
from data import MnistVAE
import numpy as np
import sys
import os

def net_call(self, x):
    return self.net(x)

def net_muv_call(self, x):
    h = self.net(x)
    mu = self.mu(h)
    var = self.var(h)
    return (mu, var)

p_net, q_net = {}, {}
# Set up distributions
q_net['z'] = Dist(callback=net_muv_call, bind=True, sampler=gaussian_sampler)
p_net['z'] = Dist(callback=lambda: (0, 1), bind=False, sampler=gaussian_sampler)
p_net['x'] = Dist(callback=net_call, bind=True, sampler=gaussian_sampler)

# Define underlying neural networks
q_net['z'].net = Sequential([Dense(500, input_dim=784),
                             BatchNormalization(),
                             Activation('relu'),
                             Dense(500),
                             BatchNormalization(),
                             Activation('relu')])
q_net['z'].mu  = Sequential([Dense(100, input_dim=500),
                             BatchNormalization()])
q_net['z'].var = Sequential([Dense(100, input_dim=500),
                             BatchNormalization(),
                             Activation('softplus'),])
p_net['x'].net = Sequential([Dense(500, input_dim=100),
                             BatchNormalization(),
                             Activation('relu'),
                             Dense(500),
                             BatchNormalization(),
                             Activation('relu'),
                             Dense(784),
                             Activation('sigmoid')])

# Set up VAE
vae = VAE(p_net=p_net, q_net=q_net, shape={'x': (784,)})
vae.compile('adam', compute_log_likelihood=True, verbose=1)

# Train VAE
dataloader = MnistVAE(100)
fh = file_handle('outputs', 'vae', 'standard')
losslog = LossLog(fh=fh)
nll = NegativeLogLikelihood(dataloader,
                            n_samples=50,
                            run_every=100,
                            run_training=True,
                            run_validation=True,
                            run_test=True,
                            display_nelbo=True,
                            display_epoch=True,
                            end_line=True,
                            patience=10,
                            step_decay=0.1,
                            fh=fh)
callbacks = [losslog, nll]

with Session(fh) as sess:
    vae.fit(dataloader,
            nb_epoch=500,
            iter_per_epoch=500,
            callbacks=callbacks)
