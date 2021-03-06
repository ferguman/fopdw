#- def has_permission(user_uuid, device_uuid, permission):

# device_group_name device_group_uuid device_uuid group_permissions

# TODO: Move this structure to the database after you get it proved out.
#       Each device belongs to one and only one group.  Each person can be in
#       0, 1 or more groups.  There are two permissions: organization and group.
#       Each permission has the permission types: admin and view.
#
# TODO: 10/11/2019 - I've hit a situation that this permissions schema does not accomadate. I want
#       to have a food computer that two organizations can both have admin and view rights to
#       and I want to have a third organization that only has view rights to the device.

#TODO: Add group related columns and tables to the fop database to hold the information that is currently hard coded in 
#      in the data structures below.

# Some Group Id's explicitly declared for handy reference
mars_gid = '30d78ab9-611d-4c44-8bec-a5a91240e1e6'
micds_gid = '09e463e7-cdbf-410c-bc2a-5b0691bffdbf' 
sare_gid = 'cdb76a7e-e454-437e-ba8c-eb3f254beb75'
slip_gid = 'ee288832-0017-4976-ac52-b670bf6c7b55'
slsc_gid = '37cad361-cc28-4730-b676-7a170cf3a37a' 
usf_gid = 'b456f6ec-6293-4077-9ad1-f1f1b01524d6' 
ghv_gid = 'a4839091-91e3-41d9-9338-d8fabc0cdc02'

device_permissions_table = [
    {'device_uuid':'f38dc0c8-658a-4acd-b1c5-c66e17287027', 'group_id':usf_gid, 'name':'usf',
     'organization_uuid':'dac952cd-8968-4c26-a508-813861015995', 'local_name':'fc3',
     'organization':{'admin':True, 'view':True}, 'group':{'admin':False, 'view':True}},
    {'device_uuid':'dda50a41-f71a-4b3e-aeea-2b58795d2c99', 'group_id':usf_gid, 'name':'usf',
     'organization_uuid':'dac952cd-8968-4c26-a508-813861015995', 'local_name':'fc1 camera',
     'organization':{'admin':True, 'view':True}, 'group':{'admin':False, 'view':True}},
    {'device_uuid':'80eb0af1-bb85-41ef-9daf-633279e913bb', 'group_id':mars_gid, 'name':'mars',
     'organization_uuid':'90e22482-087b-484c-8f89-8e88c02164b8', 'local_name':'slsc mvp camera',
     'organization':{'admin':False, 'view':True}, 'group':{'admin':True, 'view':True}},
    {'device_uuid':'25895b2b-3267-45e3-ab25-b1958829d932', 'group_id':micds_gid, 'name':'micds',
     'organization_uuid':'f873cc7f-7ee4-4e88-8357-e308126974ff', 'local_name':'micds_1 camera',
     'organization':{'admin':False, 'view':True}, 'group':{'admin':True, 'view':True}},
    {'device_uuid':'869db738-274d-4bca-ac4f-a0b0d39db232', 'group_id':micds_gid, 'name':'micds',
     'organization_uuid':'f873cc7f-7ee4-4e88-8357-e308126974ff', 'local_name':'micds2_camera',
     'organization':{'admin':False, 'view':True}, 'group':{'admin':True, 'view':True}},
    {'device_uuid':'454ce6b1-2a0d-44eb-b85d-847d39150dd6', 'group_id':micds_gid, 'name':'micds',
     'organization_uuid':'f873cc7f-7ee4-4e88-8357-e308126974ff', 'local_name':'micds3_camera',
     'organization':{'admin':False, 'view':True}, 'group':{'admin':True, 'view':True}},
    {'device_uuid':'b3620a50-ab7f-480e-ae97-ad82966ee2ec', 'group_id':micds_gid, 'name':'micds',
     'organization_uuid':'f873cc7f-7ee4-4e88-8357-e308126974ff', 'local_name':'micds4_camera',
     'organization':{'admin':False, 'view':True}, 'group':{'admin':True, 'view':True}},
    {'device_uuid':'ce81f410-9ff3-4e70-b05d-5b2e39d8331d', 'group_id':micds_gid, 'name':'micds',
     'organization_uuid':'f873cc7f-7ee4-4e88-8357-e308126974ff', 'local_name':'micds5_camera',
     'organization':{'admin':False, 'view':True}, 'group':{'admin':True, 'view':True}},
    {'device_uuid':'ff985248-4456-41c1-bf52-ec175cfec287', 'group_id':ghv_gid, 'name':'ghv',
     'organization_uuid':'dafdea50-85d6-460a-8dd6-e79d978c0fcf', 'local_name':'sludev1_camera',
     'organization':{'admin':True, 'view':True}, 'group':{'admin':True, 'view':True}},
    {'device_uuid':'3f5aafe6-27ac-4a16-9b2a-d1ebbb8daee3', 'group_id':usf_gid, 'name':'usf',
     'organization_uuid':'dac952cd-8968-4c26-a508-813861015995', 'local_name':'doser1',
     'organization':{'admin':True, 'view':True}, 'group':{'admin':True, 'view':True}},
    ]

person_groups_table = [
    {'person_uuid':'034a658b-0bce-4214-9276-eebd4b574bf9', 'name':'peter', 
     'organization_uuid':'18ffe759-bf6f-4f34-9a60-7c43d48a7fb0', 'group_name':'mars', 'group_id':mars_gid},
    {'person_uuid':'034a658b-0bce-4214-9276-eebd4b574bf9', 'name':'peter', 
     'organization_uuid':'18ffe759-bf6f-4f34-9a60-7c43d48a7fb0', 'group_name':'micds', 'group_id':micds_gid},
    {'person_uuid':'645f9b8f-ab97-4c81-b8af-d82989812f90', 'name':'paul', 
     'organization_uuid':'f873cc7f-7ee4-4e88-8357-e308126974ff', 'group_name':'micds', 'group_id':micds_gid},
    {'person_uuid':'4b108cf5-6e6b-475c-8044-f009b90c1dd0', 'name':'ferguman', 
     'organization_uuid':'dac952cd-8968-4c26-a508-813861015995', 'group_name':'usf', 'group_id':usf_gid},
    {'person_uuid':'4b108cf5-6e6b-475c-8044-f009b90c1dd0', 'name':'ferguman', 
     'organization_uuid':'dac952cd-8968-4c26-a508-813861015995', 'group_name':'mars', 'group_id':mars_gid},
    {'person_uuid':'4b108cf5-6e6b-475c-8044-f009b90c1dd0', 'name':'ferguman', 
     'organization_uuid':'dac952cd-8968-4c26-a508-813861015995', 'group_name':'micds', 'group_id':micds_gid},
    {'person_uuid':'4b108cf5-6e6b-475c-8044-f009b90c1dd0', 'name':'ferguman', 
     'organization_uuid':'dac952cd-8968-4c26-a508-813861015995', 'group_name':'slip', 'group_id':slip_gid},
    {'person_uuid':'04f66e90-b537-471c-8c11-76c6d0f19caf', 'name':'james', 
     'organization_uuid':'45bf589064c643739780b100eab0baee', 'group_name':'usf', 'group_id':usf_gid},
    {'person_uuid':'c91cc7b0-9113-49e0-99e1-4f634a8c9aa3', 'name':'jim', 
     'organization_uuid':'dac952cd-8968-4c26-a508-813861015995', 'group_name':'usf', 'group_id':usf_gid},
    {'person_uuid':'299ca963-49c7-487f-8adc-13cb39d28e18', 'name':'phil', 
     'organization_uuid':'dafdea50-85d6-460a-8dd6-e79d978c0fcf', 'group_name':'ghv', 'group_id':ghv_gid},
    {'person_uuid':'ad6ef000-80a1-4389-93c8-ae770dbfaf4f', 'name':'sluhdev', 
     'organization_uuid':'dafdea50-85d6-460a-8dd6-e79d978c0fcf', 'group_name':'ghv', 'group_id':ghv_gid},
    {'person_uuid':'4b108cf5-6e6b-475c-8044-f009b90c1dd0', 'name':'ferguman', 
     'organization_uuid':'dac952cd-8968-4c26-a508-813861015995', 'group_name':'ghv', 'group_id':ghv_gid},
    ]

person_table = [
    {'person_uuid':'645f9b8f-ab97-4c81-b8af-d82989812f90', 
     'organization_uuid':'f873cc7f-7ee4-4e88-8357-e308126974ff'},
    {'person_uuid':'4b108cf5-6e6b-475c-8044-f009b90c1dd0', 
     'organization_uuid':'dac952cd-8968-4c26-a508-813861015995'},
    {'person_uuid':'d2f0fd09-2892-4d35-85c7-c53b0b739b43', 
     'organization_uuid':'90e22482-087b-484c-8f89-8e88c02164b8'},
    {'person_uuid':'034a658b-0bce-4214-9276-eebd4b574bf9', 
     'organization_uuid':'18ffe759-bf6f-4f34-9a60-7c43d48a7fb0'},
    {'person_uuid':'04f66e90-b537-471c-8c11-76c6d0f19caf', 
     'organization_uuid':'45bf589064c643739780b100eab0baee'},
    {'person_uuid':'c91cc7b0-9113-49e0-99e1-4f634a8c9aa3', 
     'organization_uuid':'dac952cd-8968-4c26-a508-813861015995'},
    {'person_uuid':'299ca963-49c7-487f-8adc-13cb39d28e18', 
     'organization_uuid':'dafdea50-85d6-460a-8dd6-e79d978c0fcf'},
    {'person_uuid':'ad6ef000-80a1-4389-93c8-ae770dbfaf4f', 
     'organization_uuid':'dafdea50-85d6-460a-8dd6-e79d978c0fcf'},
    ]


def get_user_groups(user_uuid):
   #- return ('30d78ab9-611d-4c44-8bec-a5a91240e1e6',)

   res = ()
   for group in person_groups_table:
      if group['person_uuid'] == user_uuid:
         res = res + (group['group_id'],)
         #- res.append(group['group_id']) 

   return res


def has_permission(user_uuid, device_uuid, permission):

    # Get the device permissions 
    this_devices_permissions = None
    for permissions in device_permissions_table:
        if permissions['device_uuid'] == device_uuid:
            this_devices_permissions = permissions
            break
    
    assert(this_devices_permissions != None), 'error - device {} has no permissions'.format(device_uuid)

    # Get the person's organization
    user_organization_uuid = None
    for person in person_table:
        if person['person_uuid'] == user_uuid:
            user_organization_uuid = person['organization_uuid']
            break

    assert(user_organization_uuid != None), 'error - user {} has no organization'.format(user_uuid)

    # Does the user have organization permissions
    has_organization_permission = False
    if user_organization_uuid == this_devices_permissions['organization_uuid']:
          has_organization_permission = this_devices_permissions['organization'][permission] 

    # Is the person a member of the device's group
    person_in_device_group = False 
    for group in person_groups_table:
        if user_uuid == group['person_uuid'] and group['group_id'] == this_devices_permissions['group_id']:
            person_in_device_group = True
            break

    # Does the person have group permissions
    has_device_group_permission = False
    if person_in_device_group:
        has_device_group_permission = this_devices_permissions['group'][permission]

    return has_organization_permission or has_device_group_permission 
