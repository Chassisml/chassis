# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: model.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0bmodel.proto\"\x0f\n\rStatusRequest\"p\n\tModelInfo\x12\x12\n\nmodel_name\x18\x01 \x01(\t\x12\x15\n\rmodel_version\x18\x02 \x01(\t\x12\x14\n\x0cmodel_author\x18\x03 \x01(\t\x12\x12\n\nmodel_type\x18\x04 \x01(\t\x12\x0e\n\x06source\x18\x05 \x01(\t\"\\\n\x10ModelDescription\x12\x0f\n\x07summary\x18\x01 \x01(\t\x12\x0f\n\x07\x64\x65tails\x18\x02 \x01(\t\x12\x11\n\ttechnical\x18\x03 \x01(\t\x12\x13\n\x0bperformance\x18\x04 \x01(\t\"c\n\nModelInput\x12\x10\n\x08\x66ilename\x18\x01 \x01(\t\x12\x1c\n\x14\x61\x63\x63\x65pted_media_types\x18\x02 \x03(\t\x12\x10\n\x08max_size\x18\x03 \x01(\t\x12\x13\n\x0b\x64\x65scription\x18\x04 \x01(\t\"Z\n\x0bModelOutput\x12\x10\n\x08\x66ilename\x18\x01 \x01(\t\x12\x12\n\nmedia_type\x18\x02 \x01(\t\x12\x10\n\x08max_size\x18\x03 \x01(\t\x12\x13\n\x0b\x64\x65scription\x18\x04 \x01(\t\"J\n\x0eModelResources\x12\x14\n\x0crequired_ram\x18\x01 \x01(\t\x12\x10\n\x08num_cpus\x18\x02 \x01(\x02\x12\x10\n\x08num_gpus\x18\x03 \x01(\x05\"+\n\x0cModelTimeout\x12\x0e\n\x06status\x18\x01 \x01(\t\x12\x0b\n\x03run\x18\x02 \x01(\t\"\x9f\x01\n\rModelFeatures\x12\x1b\n\x13\x61\x64versarial_defense\x18\x01 \x01(\x08\x12\x12\n\nbatch_size\x18\x02 \x01(\x05\x12\x13\n\x0bretrainable\x18\x03 \x01(\x08\x12\x16\n\x0eresults_format\x18\x04 \x01(\t\x12\x14\n\x0c\x64rift_format\x18\x05 \x01(\t\x12\x1a\n\x12\x65xplanation_format\x18\x06 \x01(\t\"\xb0\x02\n\x0eStatusResponse\x12\x13\n\x0bstatus_code\x18\x01 \x01(\x05\x12\x0e\n\x06status\x18\x02 \x01(\t\x12\x0f\n\x07message\x18\x03 \x01(\t\x12\x1e\n\nmodel_info\x18\x04 \x01(\x0b\x32\n.ModelInfo\x12&\n\x0b\x64\x65scription\x18\x05 \x01(\x0b\x32\x11.ModelDescription\x12\x1b\n\x06inputs\x18\x06 \x03(\x0b\x32\x0b.ModelInput\x12\x1d\n\x07outputs\x18\x07 \x03(\x0b\x32\x0c.ModelOutput\x12\"\n\tresources\x18\x08 \x01(\x0b\x32\x0f.ModelResources\x12\x1e\n\x07timeout\x18\t \x01(\x0b\x32\r.ModelTimeout\x12 \n\x08\x66\x65\x61tures\x18\n \x01(\x0b\x32\x0e.ModelFeatures\"_\n\tInputItem\x12$\n\x05input\x18\x01 \x03(\x0b\x32\x15.InputItem.InputEntry\x1a,\n\nInputEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\x0c:\x02\x38\x01\"O\n\nRunRequest\x12\x1a\n\x06inputs\x18\x01 \x03(\x0b\x32\n.InputItem\x12\x14\n\x0c\x64\x65tect_drift\x18\x02 \x01(\x08\x12\x0f\n\x07\x65xplain\x18\x03 \x01(\x08\"u\n\nOutputItem\x12\'\n\x06output\x18\x01 \x03(\x0b\x32\x17.OutputItem.OutputEntry\x12\x0f\n\x07success\x18\x02 \x01(\x08\x1a-\n\x0bOutputEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\x0c:\x02\x38\x01\"a\n\x0bRunResponse\x12\x13\n\x0bstatus_code\x18\x01 \x01(\x05\x12\x0e\n\x06status\x18\x02 \x01(\t\x12\x0f\n\x07message\x18\x03 \x01(\t\x12\x1c\n\x07outputs\x18\x04 \x03(\x0b\x32\x0b.OutputItem\"\x11\n\x0fShutdownRequest\"H\n\x10ShutdownResponse\x12\x13\n\x0bstatus_code\x18\x01 \x01(\x05\x12\x0e\n\x06status\x18\x02 \x01(\t\x12\x0f\n\x07message\x18\x03 \x01(\t2\x8a\x01\n\nModzyModel\x12)\n\x06Status\x12\x0e.StatusRequest\x1a\x0f.StatusResponse\x12 \n\x03Run\x12\x0b.RunRequest\x1a\x0c.RunResponse\x12/\n\x08Shutdown\x12\x10.ShutdownRequest\x1a\x11.ShutdownResponseB\x18\n\x14\x63om.modzy.model.grpcP\x01\x62\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'model_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  DESCRIPTOR._serialized_options = b'\n\024com.modzy.model.grpcP\001'
  _INPUTITEM_INPUTENTRY._options = None
  _INPUTITEM_INPUTENTRY._serialized_options = b'8\001'
  _OUTPUTITEM_OUTPUTENTRY._options = None
  _OUTPUTITEM_OUTPUTENTRY._serialized_options = b'8\001'
  _STATUSREQUEST._serialized_start=15
  _STATUSREQUEST._serialized_end=30
  _MODELINFO._serialized_start=32
  _MODELINFO._serialized_end=144
  _MODELDESCRIPTION._serialized_start=146
  _MODELDESCRIPTION._serialized_end=238
  _MODELINPUT._serialized_start=240
  _MODELINPUT._serialized_end=339
  _MODELOUTPUT._serialized_start=341
  _MODELOUTPUT._serialized_end=431
  _MODELRESOURCES._serialized_start=433
  _MODELRESOURCES._serialized_end=507
  _MODELTIMEOUT._serialized_start=509
  _MODELTIMEOUT._serialized_end=552
  _MODELFEATURES._serialized_start=555
  _MODELFEATURES._serialized_end=714
  _STATUSRESPONSE._serialized_start=717
  _STATUSRESPONSE._serialized_end=1021
  _INPUTITEM._serialized_start=1023
  _INPUTITEM._serialized_end=1118
  _INPUTITEM_INPUTENTRY._serialized_start=1074
  _INPUTITEM_INPUTENTRY._serialized_end=1118
  _RUNREQUEST._serialized_start=1120
  _RUNREQUEST._serialized_end=1199
  _OUTPUTITEM._serialized_start=1201
  _OUTPUTITEM._serialized_end=1318
  _OUTPUTITEM_OUTPUTENTRY._serialized_start=1273
  _OUTPUTITEM_OUTPUTENTRY._serialized_end=1318
  _RUNRESPONSE._serialized_start=1320
  _RUNRESPONSE._serialized_end=1417
  _SHUTDOWNREQUEST._serialized_start=1419
  _SHUTDOWNREQUEST._serialized_end=1436
  _SHUTDOWNRESPONSE._serialized_start=1438
  _SHUTDOWNRESPONSE._serialized_end=1510
  _MODZYMODEL._serialized_start=1513
  _MODZYMODEL._serialized_end=1651
# @@protoc_insertion_point(module_scope)