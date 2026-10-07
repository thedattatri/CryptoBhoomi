const { Web3 } = require('web3');
const fs = require('fs');

async function debugState() {
  const web3 = new Web3('http://127.0.0.1:7545');
  
  const artifact = JSON.parse(fs.readFileSync('build/contracts/LandRegistry.json', 'utf8'));
  const abi = artifact.abi;
  const address = artifact.networks['5777'].address;
  const contract = new web3.eth.Contract(abi, address);

  const propArtifact = JSON.parse(fs.readFileSync('build/contracts/Property.json', 'utf8'));
  
  console.log("--- DEBUGGING BLOCKCHAIN STATE ---");
  try {
    const mappedAddr = await contract.methods.revenueDeptIdToEmployee(200).call();
    console.log("Mapped Officer for Dept 200:", mappedAddr);
  } catch (e) {
    console.log("Error fetching mapping:", e.message);
  }

  try {
    const props = await contract.methods.getPropertiesByRevenueDeptId(200).call();
    console.log("Properties under Dept 200:", props.length);
    if (props.length > 0) {
      console.log("Property IDs:", props.map(p => p.propertyId));
    }
  } catch (e) {
    console.log("Error fetching properties:", e.message);
  }

  try {
    const propAddress = await contract.methods.getPropertiesContract().call();
    console.log("Property Contract Address:", propAddress);
    const propContract = new web3.eth.Contract(propArtifact.abi, propAddress);
    
    // Check if property 2 exists directly
    try {
       const p2 = await propContract.methods.getLandDetailsAsStruct(2).call();
       console.log("Property 2 from Property.sol:", p2.propertyId !== '0' ? "EXISTS" : "Does Not Exist");
    } catch(e) {
       console.log("Property 2 check error:", e.message);
    }
  } catch(e) {}
}

debugState();
