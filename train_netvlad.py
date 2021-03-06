import mxnet as mx
import numpy as np
import os

from easydict import EasyDict as edict
Flag_contiue  =False
config = edict()
config.NUM_VLAD_CENTERS = 128
config.NUM_LABEL =500
config.LEARNING_RATE = 1
config.FEA_LEN = 512
config.MAX_SHAPE = 800
config.BATCH_SIZE = 32
config.DROP_OUT_RATIO = 0

def _save_model(model_prefix, rank=0):
	import os
	if model_prefix is None:
		return None
	dst_dir = os.path.dirname(model_prefix)
	if not os.path.isdir(dst_dir):
		os.mkdir(dst_dir)
	return mx.callback.do_checkpoint(model_prefix if rank == 0 else "%s-%d" % (
		model_prefix, rank))


def tensor_vstack(tensor_list, pad=0):
    """
    vertically stack tensors
    :param tensor_list: list of tensor to be stacked vertically
    :param pad: label to pad with
    :return: tensor with max shape
    """
    ndim = len(tensor_list[0].shape)
    dtype = tensor_list[0].dtype
    islice = tensor_list[0].shape[0]
    dimensions = []
    first_dim = sum([tensor.shape[0] for tensor in tensor_list])
    dimensions.append(first_dim)
    for dim in range(1, ndim):
        dimensions.append(max([tensor.shape[dim] for tensor in tensor_list]))
    if pad == 0:
        all_tensor = np.zeros(tuple(dimensions), dtype=dtype)
    elif pad == 1:
        all_tensor = np.ones(tuple(dimensions), dtype=dtype)
    else:
        all_tensor = np.full(tuple(dimensions), pad, dtype=dtype)
    if ndim == 1:
        for ind, tensor in enumerate(tensor_list):
            all_tensor[ind*islice:(ind+1)*islice] = tensor
    elif ndim == 2:
        for ind, tensor in enumerate(tensor_list):
            all_tensor[ind*islice:(ind+1)*islice, tensor.shape[1]] = tensor
    elif ndim == 3:
        for ind, tensor in enumerate(tensor_list):
            all_tensor[ind*islice:(ind+1)*islice, :tensor.shape[1], :tensor.shape[2]] = tensor
    elif ndim == 4:
        for ind, tensor in enumerate(tensor_list):
            all_tensor[ind*islice:(ind+1)*islice, :tensor.shape[1], :tensor.shape[2], :tensor.shape[3]] = tensor
    else:
        raise Exception('Sorry, unimplemented.')
    return all_tensor


class FeaDataIter(mx.io.DataIter):
	def __init__(self, filelist, batchsize, ctx, num_classes ,data_shape, phase = 'train', dtype = 'float32', work_load_list =None):
		self.batch_size = batchsize
		self.cur_iter = 0
#		self.max_iter = max_iter
		self.dtype = dtype
		self.ctx = ctx
		self.work_load_list = work_load_list
		self.featuredb =[]
		if not os.path.exists(filelist):
			raise Exception('Sorry, filelist {} not exsit.'.format(filelist))
		f = open(filelist)
		self.featuredb = f.readlines()
		f.close()
                self.maxshape = data_shape[0]
		self.total= len(self.featuredb)
		self.num_classes = num_classes
                self.cur =0
                self.phase = phase
		label = np.random.randint(0, 1, [self.batch_size, ])
		data = np.random.uniform(-1, 1, [self.batch_size, data_shape[0],data_shape[1]])
		self.data = [mx.nd.array(data, dtype=self.dtype)]
		self.label =[ mx.nd.array(label, dtype=self.dtype)]
                self.reset()
	def __iter__(self):
		return self
	@property
	def provide_data(self):
		return [mx.io.DataDesc('data', self.data[0].shape, self.dtype,layout='NTC')]
	@property
	def provide_label(self):
                #print(self.label[0].shape)
		return [mx.io.DataDesc('softmax_label', self.label[0].shape , self.dtype)]

	def iter_next(self):
		return self.cur + self.batch_size <= self.total

        def getindex(self):
            return self.cur / self.batch_size

        def getpad(self):
            if self.cur + self.batch_size > self.total:
                return self.cur + self.batch_size - self.total
            else:
                return 0

	def next(self):
                i =0
		if self.iter_next():
			self.get_batch()
			self.cur += self.batch_size
#			return self.im_info, \
                        i+=1
			return  mx.io.DataBatch(data=self.data, label=self.label,
			                       pad=self.getpad(), index=self.getindex(),
			                       provide_data=self.provide_data, provide_label=self.provide_label)
		else:
                    if not i :
                        print(self.phase)
                        self.reset()
			raise StopIteration

	def __next__(self):
		return self.next()
	def reset(self):
		self.cur = 0
                import random 
		random.shuffle(self.featuredb)


	def get_data_label(self,iroidb):
                num_samples = len(iroidb)
		label_array = []
		data_array =[]
		for line in iroidb:
                    datapath  = line.split(',')[0]
                    datapath = '/workspace/data/trainval/' + datapath +'_pool5_senet.binary' 
#                    label_tensor = np.zeros((1))
#                    label_tensor[:] = int(line.split(",")[1])
		    label_array.append([float(line.split(',')[1])-1])
                    data = np.fromfile(datapath,dtype='float32').reshape(-1,config.FEA_LEN)
#                    for i in range(data.shape[0]):
#                        row = data[i,:]
#                        mean_r = np.mean(row)
#                        var_r = np.var(row)
                        #print(mean_r)
#                        data[i,:] = (row-mean_r)/var_r
                    data_tensor = np.zeros((self.maxshape,data.shape[1]))
                    randidx =[]
                    if data.shape[0] >0:
                    	for i in range(self.maxshape):
                            import random
                            randidx.append(random.randint(0,data.shape[0]-1))
               #     print(randidx)
                        data_tensor = data[randidx,:]
               #     print(data_tensor)
            #        if data.shape[0] > self.maxshape:
             #           import random
              #          radstart = random.randint(0, data.shape[0] - self.maxshape -1 )
               #         data_tensor = data[radstart:radstart+self.maxshape,:]
                #    else:
                #        data_tensor[0:data.shape[0],:] = data
#                   data_tensor[0,0,:,:] = data
#                    print(data_tensor.shape)
		    data_array.append(data_tensor)
                # print(label_array)
		return np.array(data_array), np.array(label_array)



	def get_batch(self):
		# slice roidb
		cur_from = self.cur
		cur_to = min(cur_from + self.batch_size, self.total)
		roidb = [self.featuredb[i] for i in range(cur_from, cur_to)]

                batch_label = mx.nd.empty(self.provide_label[0][1])
		# decide multi device slice
		work_load_list = self.work_load_list
		ctx = self.ctx
		if work_load_list is None:
			work_load_list = [1] * len(ctx)
		assert isinstance(work_load_list, list) and len(work_load_list) == len(ctx), \
			"Invalid settings for work load. "
		slices = mx.executor_manager._split_input_slice(self.batch_size, work_load_list)

		# get testing data for multigpu
		# each element in the list is the data used by different gpu
		data_list = []
		label_list = []
		for islice in slices:
			iroidb = [roidb[i] for i in range(islice.start, islice.stop)]
			data, label = self.get_data_label(iroidb)
			data_list.append(data)
			label_list.append(label)
                #print(data_list.shape())
		# pad data first and then assign anchor (read label)
                
		data_tensor = tensor_vstack(data_list)
                              
                label_tensor = np.vstack(label_list)
                for i  in range(len(label_tensor)):
                    label = label_tensor[i]
                    # print(label)
                    batch_label[i] = label
#		label_tensor = [batch for batch in label_list]
       #         print(batch_label)

		self.data =[mx.nd.array([batch for batch in data_tensor])]
#                print('data finish')
#                print(batch_label)
		self.label = [batch_label]
#                print('label finish')

 
def netvlad_mutil(batchsize, num_centers, num_output,**kwargs):
	input_data = mx.symbol.Variable(name="data")
	input_data_half = mx.symbol.Reshape(data = input_data,shape=(0,-1,config.FEA_LEN/2))
	input_data_four = mx.symbol.Reshape(data = input_data,shape=(0,-1,config.FEA_LEN/4))
	input_data_eight = mx.symbol.Reshape(data = input_data,shape=(0,-1,config.FEA_LEN/8))
#        input_data = mx.symbol.BatchNorm(input_data)
	input_centers = mx.symbol.Variable(name="centers",shape=(num_centers/2,config.FEA_LEN),init = mx.init.Normal(1))

        w = mx.symbol.Variable('weights_vlad',
                            shape=[num_centers/2, config.FEA_LEN],init= mx.initializer.Normal(0.1))
        b = mx.symbol.Variable('biases', shape=[1,num_centers/2],init = mx.initializer.Constant(1e-4))

       
	weights = mx.symbol.dot(name='w', lhs=input_data, rhs = w, transpose_b = True)
        weights = mx.symbol.broadcast_add(weights,b)

	softmax_weights = mx.symbol.softmax(data=weights, axis=2,name='softmax_vald')
#	softmax_weights = mx.symbol.SoftmaxOutput(data=weights, axis=0,name='softmax_vald')

	vari_lib =[]

	for i in range(num_centers/2):
		y = mx.symbol.slice_axis(name= 'slice_center_{}'.format(i),data=input_centers,axis=0,begin=i,end=i+1)
		temp_w = mx.symbol.slice_axis(name= 'temp_w_{}'.format(i),data=softmax_weights,axis=2,begin=i,end=i+1)
		element_sub = mx.symbol.broadcast_sub(input_data, y,name='cast_sub_{}'.format(i))
		vari_lib.append(mx.symbol.batch_dot(element_sub, temp_w,transpose_a = True,name='batch_dot_{}'.format(i)))

   #     group = mx.sym.Group(vari_lib)
        concat = []
        concat.append(vari_lib[0])
#        concat = mx.symbol.concat(data= vari_lib,dim=2,num_args=5,name = 'concat')
	for i in range(len(vari_lib)-1):
	    concat.append(mx.symbol.concat(concat[i],vari_lib[i+1],dim=2,name = 'concat_{}'.format(i)))
        
        netvlad_ori = concat[len(concat)-1]

	netvlad_ori = mx.symbol.L2Normalization(netvlad_ori,mode='channel')
        netvlad_ori = mx.symbol.Reshape(data = netvlad_ori,shape=(0,-1,config.FEA_LEN))
#################################original part ####################
        input_centers_half = mx.symbol.Variable(name="centers_half",shape=(num_centers/2,config.FEA_LEN/2),init = mx.init.Normal(1))

        w_half = mx.symbol.Variable('weights_vlad_half',
                            shape=[num_centers/2, config.FEA_LEN/2],init= mx.initializer.Normal(0.1))
        b_half = mx.symbol.Variable('biases_half', shape=[1,num_centers/2],init = mx.initializer.Constant(1e-4))


        weights_half = mx.symbol.dot(name='w_half', lhs=input_data_half, rhs = w_half, transpose_b= True)
        weights_half = mx.symbol.broadcast_add(weights_half,b_half)

        softmax_weights_half = mx.symbol.softmax(data=weights_half, axis=2,name='softmax_vald_half')
#       softmax_weights = mx.symbol.SoftmaxOutput(data=weights, axis=0,name='softmax_vald')

        vari_lib_half =[]
        for i in range(num_centers/2):
                y_half = mx.symbol.slice_axis(name= 'slice_center_half_{}'.format(i),data=input_centers_half,axis=0,begin=i,end=i+1)
                temp_w_half = mx.symbol.slice_axis(name= 'temp_w_half{}'.format(i),data=softmax_weights_half,axis=2,begin=i,end=i+1)
                element_sub_half = mx.symbol.broadcast_sub(input_data_half, y_half,name='cast_sub_half_{}'.format(i))
                vari_lib_half.append(mx.symbol.batch_dot(element_sub_half, temp_w_half,transpose_a = True,name='batch_dot_half_{}'.format(i)))

   #     group = mx.sym.Group(vari_lib)
        concat_half = []
        concat_half.append(vari_lib_half[0])
#        concat = mx.symbol.concat(data= vari_lib,dim=2,num_args=5,name = 'concat')
        for i in range(len(vari_lib_half)-1):
            concat_half.append(mx.symbol.concat(concat_half[i],vari_lib_half[i+1],dim=2,name ='concat_half{}'.format(i)))


        netvlad_half = concat_half[len(concat_half)-1]
	netvlad_half = mx.symbol.L2Normalization(netvlad_half,mode='channel')
        netvlad_half = mx.symbol.Reshape(data= netvlad_half,shape=(0,-1,config.FEA_LEN))
########################## 1/4 feature size #############################

        input_centers_four = mx.symbol.Variable(name="centers_four",shape=(num_centers/2,config.FEA_LEN/4),init = mx.init.Normal(1))

        w_four= mx.symbol.Variable('weights_vlad_four',
                            shape=[num_centers/2, config.FEA_LEN/4],init= mx.initializer.Normal(0.1))
        b_four = mx.symbol.Variable('biases_four', shape=[1,num_centers/2],init = mx.initializer.Constant(1e-4))


        weights_four = mx.symbol.dot(name='w_four', lhs=input_data_four, rhs = w_four, transpose_b= True)
        weights_four = mx.symbol.broadcast_add(weights_four,b_four)

        softmax_weights_four = mx.symbol.softmax(data=weights_four, axis=2,name='softmax_vald_four')
#       softmax_weights = mx.symbol.SoftmaxOutput(data=weights, axis=0,name='softmax_vald')

        vari_lib_four =[]
        for i in range(num_centers/2):
                y_four = mx.symbol.slice_axis(name= 'slice_center_four_{}'.format(i),data=input_centers_four,axis=0,begin=i,end=i+1)
                temp_w_four = mx.symbol.slice_axis(name= 'temp_w_four{}'.format(i),data=softmax_weights_four,axis=2,begin=i,end=i+1)
                element_sub_four = mx.symbol.broadcast_sub(input_data_four, y_four,name='cast_sub_four_{}'.format(i))
                vari_lib_four.append(mx.symbol.batch_dot(element_sub_four, temp_w_four,transpose_a = True,name='batch_dot_four_{}'.format(i)))

   #     group = mx.sym.Group(vari_lib)
        concat_four = []
        concat_four.append(vari_lib_four[0])
#        concat = mx.symbol.concat(data= vari_lib,dim=2,num_args=5,name = 'concat')
        for i in range(len(vari_lib_four)-1):
            concat_four.append(mx.symbol.concat(concat_four[i],vari_lib_four[i+1],dim=2,name ='concat_four{}'.format(i)))


        netvlad_four = concat_four[len(concat_four)-1]
	netvlad_four = mx.symbol.L2Normalization(netvlad_four,mode='channel')
        netvlad_four = mx.symbol.Reshape(data = netvlad_four,shape = (0,-1,config.FEA_LEN))
######################## 1/8 feature ##################################

        input_centers_eight = mx.symbol.Variable(name="centers_eight",shape=(num_centers,config.FEA_LEN/8),init = mx.init.Normal(1))

        w_eight = mx.symbol.Variable('weights_vlad_eight',
                            shape=[num_centers, config.FEA_LEN/8],init= mx.initializer.Normal(0.1))
        b_eight = mx.symbol.Variable('biases_eight', shape=[1,num_centers],init = mx.initializer.Constant(1e-4))


        weights_eight = mx.symbol.dot(name='w_eight', lhs=input_data_eight, rhs = w_eight, transpose_b= True)
        weights_eight = mx.symbol.broadcast_add(weights_eight,b_eight)

        softmax_weights_eight = mx.symbol.softmax(data=weights_eight, axis=2,name='softmax_vald_eight')
#       softmax_weights = mx.symbol.SoftmaxOutput(data=weights, axis=0,name='softmax_vald')

        vari_lib_eight =[]
        for i in range(num_centers):
                y_eight = mx.symbol.slice_axis(name= 'slice_center_eight_{}'.format(i),data=input_centers_eight,axis=0,begin=i,end=i+1)
                temp_w_eight = mx.symbol.slice_axis(name= 'temp_w_eight{}'.format(i),data=softmax_weights_eight,axis=2,begin=i,end=i+1)
                element_sub_eight = mx.symbol.broadcast_sub(input_data_eight, y_eight,name='cast_sub_eight_{}'.format(i))
                vari_lib_eight.append(mx.symbol.batch_dot(element_sub_eight, temp_w_eight,transpose_a = True,name='batch_dot_eight_{}'.format(i)))

   #     group = mx.sym.Group(vari_lib)
        concat_eight = []
        concat_eight.append(vari_lib_eight[0])
#        concat = mx.symbol.concat(data= vari_lib,dim=2,num_args=5,name = 'concat')
        for i in range(len(vari_lib_eight)-1):
            concat_eight.append(mx.symbol.concat(concat_eight[i],vari_lib_eight[i+1],dim=2,name ='concat_eight{}'.format(i)))


        netvlad_eight = concat_eight[len(concat_eight)-1]

	netvlad_eight = mx.symbol.L2Normalization(netvlad_eight,mode='channel')
        netvlad_eight = mx.symbol.Reshape(data = netvlad_eight,shape=(0,-1,config.FEA_LEN))

        norm = mx.symbol.concat(netvlad_ori,netvlad_half,netvlad_four,netvlad_eight,dim=1,name='total_concat')

#        return norm

	#norm = mx.symbol.Flatten(norm)
	#norm = mx.symbol.L2Normalization(norm,mode='channel')
	norm = mx.symbol.Flatten(norm)
#        norm = mx.symbol.max(input_data,axis =1)
	norm = mx.symbol.L2Normalization(norm)
	norm = mx.symbol.Dropout(norm,p=config.DROP_OUT_RATIO)

	weights_out = mx.symbol.FullyConnected(name='w_pre', data=norm, num_hidden=num_output)
	softmax_label = mx.symbol.SoftmaxOutput(data=weights_out,name='softmax')

#	group = mx.symbol.Group([softmax_label, mx.symbol.BlockGrad(softmax_weights)])

	return softmax_label

        
def netvlad(batchsize, num_centers, num_output,**kwargs):
	input_data = mx.symbol.Variable(name="data")
        
#        input_data = mx.symbol.BatchNorm(input_data)
	input_centers = mx.symbol.Variable(name="centers",shape=(num_centers,config.FEA_LEN),init = mx.init.Normal(1))

        w = mx.symbol.Variable('weights_vlad',
                            shape=[num_centers, config.FEA_LEN],init= mx.initializer.Normal(0.1))
        b = mx.symbol.Variable('biases', shape=[1,num_centers],init = mx.initializer.Constant(1e-4))

       
	weights = mx.symbol.dot(name='w', lhs=input_data, rhs = w, transpose_b = True)
        weights = mx.symbol.broadcast_add(weights,b)

	softmax_weights = mx.symbol.softmax(data=weights, axis=2,name='softmax_vald')
#	softmax_weights = mx.symbol.SoftmaxOutput(data=weights, axis=0,name='softmax_vald')

	vari_lib =[]

	for i in range(num_centers):
		y = mx.symbol.slice_axis(name= 'slice_center_{}'.format(i),data=input_centers,axis=0,begin=i,end=i+1)
		temp_w = mx.symbol.slice_axis(name= 'temp_w_{}'.format(i),data=softmax_weights,axis=2,begin=i,end=i+1)
		element_sub = mx.symbol.broadcast_sub(input_data, y,name='cast_sub_{}'.format(i))
		vari_lib.append(mx.symbol.batch_dot(element_sub, temp_w,transpose_a = True,name='batch_dot_{}'.format(i)))

   #     group = mx.sym.Group(vari_lib)
        concat = []
        concat.append(vari_lib[0])
#        concat = mx.symbol.concat(data= vari_lib,dim=2,num_args=5,name = 'concat')
	for i in range(len(vari_lib)-1):
	    concat.append(mx.symbol.concat(concat[i],vari_lib[i+1],dim=2,name = 'concat_{}'.format(i)))
        
	norm = mx.symbol.L2Normalization(concat[len(concat)-1],mode='channel')
	norm = mx.symbol.Flatten(norm)
#        norm = mx.symbol.max(input_data,axis =1)
	norm = mx.symbol.L2Normalization(norm)
	norm = mx.symbol.Dropout(norm,p=0.8)

	weights_out = mx.symbol.FullyConnected(name='w_pre', data=norm, num_hidden=num_output)
	softmax_label = mx.symbol.SoftmaxOutput(data=weights_out,name='softmax')

#	group = mx.symbol.Group([softmax_label, mx.symbol.BlockGrad(softmax_weights)])

	return softmax_label


def _load_model(model_prefix,load_epoch,rank=0):
	import os
	assert model_prefix is not None
	sym, arg_params, aux_params = mx.model.load_checkpoint(
		model_prefix, load_epoch)
 #   logging.info('Loaded model %s_%04d.params', model_prefix, args.load_epoch)
	return (sym, arg_params, aux_params)

def _get_lr_scheduler(lr, lr_factor=None, begin_epoch = 0 ,lr_step_epochs='',epoch_size=0):
	if not lr_factor or lr_factor >= 1:
		return (lr, None)

	step_epochs = [int(l) for l in lr_step_epochs.split(',')]
	adjustlr =lr
	for s in step_epochs:
		if begin_epoch >= s:
			adjustlr *= lr_factor
	if lr != adjustlr:
		logging.info('Adjust learning rate to %e for epoch %d' % (lr, begin_epoch))

	steps = [epoch_size * (x - begin_epoch) for x in step_epochs if x - begin_epoch > 0]
	return (lr, mx.lr_scheduler.MultiFactorScheduler(step=steps, factor=lr_factor))



def train():
        import logging
        logging.basicConfig()
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        print("training begin")
	kv_store = 'device'
	# kvstore
	kv = mx.kvstore.create(kv_store)

	model_prefix = 'model/netvlad'
	optimizer = 'sgd'
	wd =0.00000005


	load_epoch =0
        gpus = '0,1,2,3'
        top_k = 5
        batch_size= config.BATCH_SIZE
        disp_batches = 50

        devs = mx.cpu() if gpus is None or gpus is '' else [
                mx.gpu(int(i)) for i in gpus.split(',')]

	train_data = FeaDataIter("new_train.txt",batch_size,devs,config.NUM_LABEL,(config.MAX_SHAPE,config.FEA_LEN))
	val_data  = FeaDataIter("new_val.txt",batch_size,devs,config.NUM_LABEL,(config.MAX_SHAPE,config.FEA_LEN),phase = 'val')
        print("loading data")
	lr, lr_scheduler = _get_lr_scheduler(config.LEARNING_RATE, 0.8,0,'5,10,20,60',train_data.total)

	optimizer_params = {
		'learning_rate': lr,
		'wd': wd,
		'lr_scheduler': lr_scheduler,
		'momentum':0.9}

	checkpoint = _save_model(model_prefix, kv.rank)
        sym_vlad = netvlad_mutil(batch_size,config.NUM_VLAD_CENTERS,config.NUM_LABEL)
        sym_vlad.save('symbol.txt')
        print(sym_vlad.get_internals())
 #       print(sym_vlad.get_internals()['total_concat' + '_output'].infer_shape_partial(data=(32,200,512)))
 #       print(type(sym_vlad.get_internals))
 #       return

#	data_shape_dict = dict(train_data.provide_data + train_data.provide_label)
#	data_shape_dict = dict(train_data.provide_data)
        #print(data_shape_dict)
#	arg_shape, out_shape, aux_shape = sym_vlad.infer_shape(**data_shape_dict)
        #print(out_shape)
	# create model
	model = mx.mod.Module(
		context=devs,
		symbol=sym_vlad 
	)

	initializer = mx.init.Xavier(
		rnd_type='gaussian', factor_type="in", magnitude=2)

	eval_metrics = ['crossentropy','accuracy']
	if top_k > 0:
	    eval_metrics.append(mx.metric.create('top_k_accuracy', top_k=top_k))

#	if optimizer == 'sgd':
#	    optimizer_params['multi_precision'] = True

	batch_end_callbacks = mx.callback.Speedometer(batch_size, disp_batches)

#	monitor = mx.mon.Monitor(args.monitor, pattern=".*") if args.monitor > 0 else None

	monitor = None

#	data_shape_dict = dict(train_data.provide_data + train_data.provide_label)

#	arg_shape, out_shape, aux_shape = model.infer_shape(**data_shape_dict)
#        print(out_shape)
#	fea_len = out_shape[1]
#	center = mx.nd.array(config.NUM_VLAD_CENTERS,fea_len)

#	arg_shape_dict = dict(zip(train_data.list_arguments(), arg_shape))
#	out_shape_dict = dict(zip(train_data.list_outputs(), out_shape))
#	aux_shape_dict = dict(zip(train_data.list_auxiliary_states(), aux_shape))

        if  Flag_contiue == True:
            load_epoch =10
	    sym, arg_params, aux_params = mx.model.load_checkpoint(model_prefix, load_epoch)
            model.fit(train_data,
			  begin_epoch=load_epoch if load_epoch else 0,
			  num_epoch=100,
			  eval_data=val_data,
			  eval_metric=eval_metrics,
			  kvstore=kv_store,
			  optimizer=optimizer,
			  optimizer_params=optimizer_params,
			  initializer=initializer,
			  arg_params=arg_params,
			  aux_params=aux_params,
			  batch_end_callback=batch_end_callbacks,
			  epoch_end_callback=checkpoint,
			  allow_missing=True,
			  monitor=monitor)

        else:

	    model.fit(train_data,
			  begin_epoch=load_epoch if load_epoch else 0,
			  num_epoch=100,
			  eval_data=val_data,
			  eval_metric=eval_metrics,
			  kvstore=kv_store,
			  optimizer=optimizer,
			  optimizer_params=optimizer_params,
			  initializer=initializer,
			  arg_params=None,
			  aux_params=None,
			  batch_end_callback=batch_end_callbacks,
			  epoch_end_callback=checkpoint,
			  allow_missing=True,
			  monitor=monitor)



if __name__ == '__main__':
        print("aa")
	train()

