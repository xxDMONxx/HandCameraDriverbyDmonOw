//============ Copyright (c) Valve Corporation, All rights reserved. ============
#include "controller_device_driver.h"

#include "driverlog.h"
#include "vrmath.h"

// Let's create some variables for strings used in getting settings.
// This is the section where all of the settings we want are stored. A section name can be anything,
// but if you want to store driver specific settings, it's best to namespace the section with the driver identifier
// ie "<my_driver>_<section>" to avoid collisions
static const char *my_controller_main_settings_section = "driver_simplecontroller";

// Individual right/left hand settings sections
static const char *my_controller_right_settings_section = "driver_simplecontroller_left_controller";
static const char *my_controller_left_settings_section = "driver_simplecontroller_right_controller";

// These are the keys we want to retrieve the values for in the settings
static const char *my_controller_settings_key_model_number = "mycontroller_model_number";
static const char *my_controller_settings_key_serial_number = "mycontroller_serial_number";


MyControllerDeviceDriver::MyControllerDeviceDriver( vr::ETrackedControllerRole role )
{
	// Set a member to keep track of whether we've activated yet or not
	is_active_ = false;

	// The constructor takes a role argument, that gives us information about if our controller is a left or right hand.
	// Let's store it for later use. We'll need it.
	my_controller_role_ = role;

	// We have our model number and serial number stored in SteamVR settings. We need to get them and do so here.
	// Other IVRSettings methods (to get int32, floats, bools) return the data, instead of modifying, but strings are
	// different.
	char model_number[ 1024 ];
	vr::VRSettings()->GetString( my_controller_main_settings_section, my_controller_settings_key_model_number, model_number, sizeof( model_number ) );
	my_controller_model_number_ = model_number;

	// Get our serial number depending on our "handedness"
	char serial_number[ 1024 ];
	vr::VRSettings()->GetString( my_controller_role_ == vr::TrackedControllerRole_LeftHand ? my_controller_left_settings_section : my_controller_right_settings_section,
		my_controller_settings_key_serial_number, serial_number, sizeof( serial_number ) );
	my_controller_serial_number_ = serial_number;

	// Initialize hand tracking data with neutral values
	hand_position_x_ = 0.0f;
	hand_position_y_ = 0.0f;
	hand_position_z_ = 0.0f;
	hand_rotation_qw_ = 1.0f;  // Identity quaternion
	hand_rotation_qx_ = 0.0f;
	hand_rotation_qy_ = 0.0f;
	hand_rotation_qz_ = 0.0f;
	trigger_value_ = 0.0f;
	grip_value_ = 0.0f;

	// Here's an example of how to use our logging wrapper around IVRDriverLog
	// In SteamVR logs (SteamVR Hamburger Menu > Developer Settings > Web console) drivers have a prefix of
	// "<driver_name>:". You can search this in the top search bar to find the info that you've logged.
	DriverLog( "My Controller Model Number: %s", my_controller_model_number_.c_str() );
	DriverLog( "My Controller Serial Number: %s", my_controller_serial_number_.c_str() );
}

//-----------------------------------------------------------------------------
// Purpose: This is called by vrserver after our
//  IServerTrackedDeviceProvider calls IVRServerDriverHost::TrackedDeviceAdded.
//-----------------------------------------------------------------------------
vr::EVRInitError MyControllerDeviceDriver::Activate( uint32_t unObjectId )
{
	// Set an member to keep track of whether we've activated yet or not
	is_active_ = true;

	// Let's keep track of our device index. It'll be useful later.
	my_controller_index_ = unObjectId;

	// Properties are stored in containers, usually one container per device index. We need to get this container to set
	// The properties we want, so we call this to retrieve a handle to it.
	vr::PropertyContainerHandle_t container = vr::VRProperties()->TrackedDeviceToPropertyContainer( my_controller_index_ );

	// Let's begin setting up the properties now we've got our container.
	// A list of properties available is contained in vr::ETrackedDeviceProperty.

	// First, let's set the model number.
	vr::VRProperties()->SetStringProperty( container, vr::Prop_ModelNumber_String, my_controller_model_number_.c_str() );

	// Let's tell SteamVR our role which we received from the constructor earlier.
	vr::VRProperties()->SetInt32Property( container, vr::Prop_ControllerRoleHint_Int32, my_controller_role_ );


	// Now let's set up our inputs

	// This tells the UI what to show the user for bindings for this controller,
	// As well as what default bindings should be for legacy apps.
	// Note, we can use the wildcard {<driver_name>} to match the root folder location
	// of our driver.
	vr::VRProperties()->SetStringProperty( container, vr::Prop_InputProfilePath_String, "{simplecontroller}/input/mycontroller_profile.json" );

	// Let's set up handles for all of our components.
	// Even though these are also defined in our input profile,
	// We need to get handles to them to update the inputs.

	// Let's set up our "A" button. We've defined it to have a touch and a click component.
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/a/touch", &input_handles_[ MyComponent_a_touch ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/a/click", &input_handles_[ MyComponent_a_click ] );

	// Let's set up our trigger. We've defined it to have a value and click component.

	// CreateScalarComponent requires:
	// EVRScalarType - whether the device can give an absolute position, or just one relative to where it was last. We
	// can do it absolute.
	// EVRScalarUnits - whether the devices has two "sides", like a joystick. This makes the range of valid inputs -1
	// to 1. Otherwise, it's 0 to 1. We only have one "side", so ours is onesided.
	vr::VRDriverInput()->CreateScalarComponent( container, "/input/trigger/value", &input_handles_[ MyComponent_trigger_value ], vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedOneSided );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/trigger/click", &input_handles_[ MyComponent_trigger_click ] );

	// Create grip value component for hand tracking
	vr::VRDriverInput()->CreateScalarComponent( container, "/input/grip/value", &input_handles_[ MyComponent_grip_value ], vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedOneSided );

	// Let's create our haptic component.
	// These are global across the device, and you can only have one per device.
	vr::VRDriverInput()->CreateHapticComponent( container, "/output/haptic", &input_handles_[ MyComponent_haptic ] );

	my_pose_update_thread_ = std::thread( &MyControllerDeviceDriver::MyPoseUpdateThread, this );

	// We've activated everything successfully!
	// Let's tell SteamVR that by saying we don't have any errors.
	return vr::VRInitError_None;
}

//-----------------------------------------------------------------------------
// Purpose: If you're an HMD, this is where you would return an implementation
// of vr::IVRDisplayComponent, vr::IVRVirtualDisplay or vr::IVRDirectModeComponent.
//
// But this a simple example to demo for a controller, so we'll just return nullptr here.
//-----------------------------------------------------------------------------
void *MyControllerDeviceDriver::GetComponent( const char *pchComponentNameAndVersion )
{
	return nullptr;
}

//-----------------------------------------------------------------------------
// Purpose: This is called by vrserver when a debug request has been made from an application to the driver.
// What is in the response and request is up to the application and driver to figure out themselves.
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::DebugRequest( const char *pchRequest, char *pchResponseBuffer, uint32_t unResponseBufferSize )
{
	if ( unResponseBufferSize >= 1 )
		pchResponseBuffer[ 0 ] = 0;
}

//-----------------------------------------------------------------------------
// Purpose: This is never called by vrserver in recent OpenVR versions,
// but is useful for giving data to vr::VRServerDriverHost::TrackedDevicePoseUpdated.
//-----------------------------------------------------------------------------
vr::DriverPose_t MyControllerDeviceDriver::GetPose()
{
	// Let's retrieve the Hmd pose to base our controller pose off.

	// First, initialize the struct that we'll be submitting to the runtime to tell it we've updated our pose.
	vr::DriverPose_t pose = { 0 };

	// These need to be set to be valid quaternions. The device won't appear otherwise.
	pose.qWorldFromDriverRotation.w = 1.f;
	pose.qDriverFromHeadRotation.w = 1.f;

	vr::TrackedDevicePose_t hmd_pose{};

	// GetRawTrackedDevicePoses expects an array.
	// We only want the hmd pose, which is at index 0 of the array so we can just pass the struct in directly, instead of in an array
	vr::VRServerDriverHost()->GetRawTrackedDevicePoses( 0.f, &hmd_pose, 1 );

	// Get the position of the hmd from the 3x4 matrix GetRawTrackedDevicePoses returns
	const vr::HmdVector3_t hmd_position = HmdVector3_From34Matrix( hmd_pose.mDeviceToAbsoluteTracking );
	// Get the orientation of the hmd from the 3x4 matrix GetRawTrackedDevicePoses returns
	const vr::HmdQuaternion_t hmd_orientation = HmdQuaternion_FromMatrix( hmd_pose.mDeviceToAbsoluteTracking );

	// Use hand tracking rotation if available, otherwise use default orientation
	vr::HmdQuaternion_t hand_rotation;
	hand_rotation.w = hand_rotation_qw_.load();
	hand_rotation.x = hand_rotation_qx_.load();
	hand_rotation.y = hand_rotation_qy_.load();
	hand_rotation.z = hand_rotation_qz_.load();

	// Apply hand rotation to the HMD orientation
	pose.qRotation = hmd_orientation * hand_rotation;

	// Use hand tracking position if available
	const vr::HmdVector3_t offset_position = {
		hand_position_x_.load(),
		hand_position_y_.load(),
		hand_position_z_.load()
	};

	// Rotate our offset by the hmd quaternion (so the controllers are always facing towards us), and add then add the position of the hmd to put it into position.
	const vr::HmdVector3_t position = hmd_position + ( offset_position * hmd_orientation );

	// copy our position to our pose
	pose.vecPosition[ 0 ] = position.v[ 0 ];
	pose.vecPosition[ 1 ] = position.v[ 1 ];
	pose.vecPosition[ 2 ] = position.v[ 2 ];

	// The pose we provided is valid.
	// This should be set is
	pose.poseIsValid = true;

	// Our device is always connected.
	// In reality with physical devices, when they get disconnected,
	// set this to false and icons in SteamVR will be updated to show the device is disconnected
	pose.deviceIsConnected = true;

	// The state of our tracking. For our virtual device, it's always going to be ok,
	// but this can get set differently to inform the runtime about the state of the device's tracking
	// and update the icons to inform the user accordingly.
	pose.result = vr::TrackingResult_Running_OK;

	return pose;
}

void MyControllerDeviceDriver::MyPoseUpdateThread()
{
	while ( is_active_ )
	{
		// Inform the vrserver that our tracked device's pose has updated, giving it the pose returned by our GetPose().
		vr::VRServerDriverHost()->TrackedDevicePoseUpdated( my_controller_index_, GetPose(), sizeof( vr::DriverPose_t ) );

		// Update our pose every five milliseconds.
		// In reality, you should update the pose whenever you have new data from your device.
		std::this_thread::sleep_for( std::chrono::milliseconds( 5 ) );
	}
}

//-----------------------------------------------------------------------------
// Purpose: This is called by vrserver when the device should enter standby mode.
// The device should be put into whatever low power mode it has.
// We don't really have anything to do here, so let's just log something.
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::EnterStandby()
{
	DriverLog( "%s hand has been put on standby", my_controller_role_ == vr::TrackedControllerRole_LeftHand ? "Left" : "Right" );
}

//-----------------------------------------------------------------------------
// Purpose: This is called by vrserver when the device should deactivate.
// This is typically at the end of a session
// The device should free any resources it has allocated here.
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::Deactivate()
{
	// Let's join our pose thread that's running
	// by first checking then setting is_active_ to false to break out
	// of the while loop, if it's running, then call .join() on the thread
	if ( is_active_.exchange( false ) )
	{
		my_pose_update_thread_.join();
	}

	// unassign our controller index (we don't want to be calling vrserver anymore after Deactivate() has been called
	my_controller_index_ = vr::k_unTrackedDeviceIndexInvalid;
}


//-----------------------------------------------------------------------------
// Purpose: This is called by our IServerTrackedDeviceProvider when its RunFrame() method gets called.
// It's not part of the ITrackedDeviceServerDriver interface, we created it ourselves.
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::MyRunFrame()
{
	// Update our inputs here with data from hand tracking
	float trigger_val = trigger_value_.load();
	float grip_val = grip_value_.load();

	// Update trigger
	vr::VRDriverInput()->UpdateScalarComponent( input_handles_[ MyComponent_trigger_value ], trigger_val, 0 );
	vr::VRDriverInput()->UpdateBooleanComponent( input_handles_[ MyComponent_trigger_click ], trigger_val > 0.5f, 0 );

	// Update grip
	vr::VRDriverInput()->UpdateScalarComponent( input_handles_[ MyComponent_grip_value ], grip_val, 0 );

	// Update A button based on gesture (you could map specific gestures here)
	vr::VRDriverInput()->UpdateBooleanComponent( input_handles_[ MyComponent_a_click ], false, 0 );
	vr::VRDriverInput()->UpdateBooleanComponent( input_handles_[ MyComponent_a_touch ], false, 0 );
}


//-----------------------------------------------------------------------------
// Purpose: This is called by our IServerTrackedDeviceProvider when it pops an event off the event queue.
// It's not part of the ITrackedDeviceServerDriver interface, we created it ourselves.
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::MyProcessEvent( const vr::VREvent_t &vrevent )
{
	switch ( vrevent.eventType )
	{
		// Listen for haptic events
		case vr::VREvent_Input_HapticVibration:
		{
			// We now need to make sure that the event was intended for this device.
			// So let's compare handles of the event and our haptic component

			if ( vrevent.data.hapticVibration.componentHandle == input_handles_[ MyComponent_haptic ] )
			{
				// The event was intended for us!
				// To convert the data to a pulse, see the docs.
				// For this driver, we'll just print the values.

				float duration = vrevent.data.hapticVibration.fDurationSeconds;
				float frequency = vrevent.data.hapticVibration.fFrequency;
				float amplitude = vrevent.data.hapticVibration.fAmplitude;

				DriverLog( "Haptic event triggered for %s hand. Duration: %.2f, Frequency: %.2f, Amplitude: %.2f", my_controller_role_ == vr::TrackedControllerRole_LeftHand ? "left" : "right",
					duration, frequency, amplitude );
			}
			break;
		}
		default:
			break;
	}
}

//-----------------------------------------------------------------------------
// Purpose: Our IServerTrackedDeviceProvider needs our serial number to add us to vrserver.
// It's not part of the ITrackedDeviceServerDriver interface, we created it ourselves.
//-----------------------------------------------------------------------------
const std::string &MyControllerDeviceDriver::MyGetSerialNumber()
{
	return my_controller_serial_number_;
}

//-----------------------------------------------------------------------------
// Purpose: Update hand position from hand tracking data
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::UpdateHandPosition( float x, float y, float z )
{
	hand_position_x_.store( x );
	hand_position_y_.store( y );
	hand_position_z_.store( z );
}

//-----------------------------------------------------------------------------
// Purpose: Update hand rotation from hand tracking data
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::UpdateHandRotation( float qw, float qx, float qy, float qz )
{
	hand_rotation_qw_.store( qw );
	hand_rotation_qx_.store( qx );
	hand_rotation_qy_.store( qy );
	hand_rotation_qz_.store( qz );
}

//-----------------------------------------------------------------------------
// Purpose: Update trigger value from gesture detection
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::UpdateTriggerValue( float value )
{
	trigger_value_.store( value );
}

//-----------------------------------------------------------------------------
// Purpose: Update grip value from gesture detection
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::UpdateGripValue( float value )
{
	grip_value_.store( value );
}